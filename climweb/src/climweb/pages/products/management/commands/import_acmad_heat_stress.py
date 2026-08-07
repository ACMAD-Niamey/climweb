import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlencode, urljoin, urlparse, urlunparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from climweb.base.models import (
    Product,
    ProductCategory,
    ProductItemType,
    ServiceCategory,
)
from climweb.pages.products.models import (
    ProductIndexPage,
    ProductItemPage,
    ProductPage,
    ProductSourceImport,
)
from climweb.pages.products.tasks import (
    _append_image_block,
    _get_products_raw,
    _save_products_raw,
)


DEFAULT_CATALOG_URL = (
    "http://154.66.220.45:8080/thredds/catalog/ACMAD/WWFD/"
    "forecastinservice/heatwave/catalog.xml"
)
OBSERVED_TMAX_URL = (
    "http://154.66.220.45:8080/thredds/fileServer/ACMAD/WWFD/"
    "forecastinservice/Tmax_forecasting/Forwebsite/Observed_Tmax.jpeg"
)
FILE_SERVER_ROOT = "http://154.66.220.45:8080/thredds/fileServer/"
SOURCE_SYSTEM = "ACMAD Heatwave THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Heat-Stress-Importer/1.0 (+https://new.acmad.org/)"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
MAX_IMAGE_SIZE = 10 * 1024 * 1024

SUMMARY_PATTERNS = (
    (
        re.compile(r"^consecutive_2_hot_days_40C_(20\d{6})_(20\d{6})\.png$"),
        "consecutive-2-hot-days-40c",
        "Consecutive 2 Hot Days — Heat Index ≥40°C",
    ),
    (
        re.compile(r"^consecutive_3_hot_days_40C_(20\d{6})_(20\d{6})\.png$"),
        "consecutive-3-hot-days-40c",
        "Consecutive 3 Hot Days — Heat Index ≥40°C",
    ),
    (
        re.compile(r"^hot_days_40C_(20\d{6})_(20\d{6})\.png$"),
        "hot-days-40c",
        "Number of Hot Days — Heat Index ≥40°C",
    ),
)
HEAT_INDEX_PATTERN = re.compile(r"^heat_index_(20\d{6})_(20\d{6})\.png$")


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def compact_date(value):
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid compact date {value!r}") from exc


def versioned_source_url(source_url, source_version):
    parsed = urlparse(source_url)
    return urlunparse(
        parsed._replace(query=urlencode({"acmad_version": source_version}))
    )


def parse_catalog_references(xml_content, catalog_url):
    """Return dated issue catalogues and yearly archive catalogues."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid THREDDS catalogue {catalog_url}: {exc}") from exc

    issue_catalogues = {}
    year_catalogues = {}
    title_key = f"{{{XLINK_NAMESPACE}}}title"
    href_key = f"{{{XLINK_NAMESPACE}}}href"
    for reference in root.findall(f".//{{{THREDDS_NAMESPACE}}}catalogRef"):
        title = reference.get(title_key, "")
        href = reference.get(href_key)
        if not href:
            continue
        child_url = urljoin(catalog_url, href)
        if re.fullmatch(r"20\d{6}", title):
            try:
                issue_catalogues[compact_date(title)] = child_url
            except ValueError:
                continue
        elif re.fullmatch(r"20\d{2}", title):
            year_catalogues[int(title)] = child_url
    return issue_catalogues, year_catalogues


def parse_issue_catalog(xml_content, expected_issue_date):
    """Extract only audited 40°C heat indicators and daily heat-index PNGs."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(
            f"Invalid heatwave issue catalogue for {expected_issue_date}: {exc}"
        ) from exc

    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath")
        if not source_path:
            continue

        definition = None
        for pattern, key, name in SUMMARY_PATTERNS:
            match = pattern.fullmatch(filename)
            if match:
                definition = (key, name, match)
                break
        if definition:
            key, name, match = definition
            category = "Heatwave Indicators"
        else:
            match = HEAT_INDEX_PATTERN.fullmatch(filename)
            if not match:
                continue
            issue_date = compact_date(match.group(1))
            valid_date = compact_date(match.group(2))
            lead_day = (valid_date - issue_date).days
            if lead_day < 0 or lead_day > 5:
                continue
            key = f"heat-index-day-{lead_day}"
            name = f"Heat Index Forecast — Day {lead_day}"
            category = "Daily Heat Index Forecasts"

        issue_date = compact_date(match.group(1))
        valid_date = compact_date(match.group(2))
        if issue_date != expected_issue_date:
            continue
        modified_node = dataset.find(f"{{{THREDDS_NAMESPACE}}}date")
        source_version = (
            modified_node.text.strip()
            if modified_node is not None and modified_node.text
            else issue_date.isoformat()
        )
        source_url = FILE_SERVER_ROOT + quote(source_path.lstrip("/"), safe="/")
        assets.append(
            {
                "key": key,
                "name": name,
                "category": category,
                "date": issue_date,
                "valid_until": valid_date,
                "filename": filename,
                "source_url": source_url,
                "source_version": source_version,
                "provenance_url": source_url,
            }
        )
    return sorted(assets, key=lambda asset: asset["key"])


class Command(BaseCommand):
    help = "Import current or historical ACMAD Heat and Thermal Stress images."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument(
            "--limit",
            type=int,
            default=3,
            help="Maximum issue dates to inspect (default: 3).",
        )
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--history-only", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument(
            "--skip-observed-tmax",
            action="store_true",
            help="Do not inspect the standalone observed maximum-temperature JPEG.",
        )
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if (
            options["from_date"]
            and options["to_date"]
            and options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        issue_catalogues, catalog_count = self._discover_issue_catalogues(options)
        issue_dates = sorted(
            issue_catalogues, reverse=not options["oldest_first"]
        )[: options["limit"]]
        self.stdout.write(
            f"Discovered {len(issue_catalogues)} matching issue date(s) across "
            f"{catalog_count} catalogue(s); inspecting {len(issue_dates)}."
        )

        assets = []
        failures = []
        for issue_date in issue_dates:
            try:
                assets.extend(
                    parse_issue_catalog(
                        self._fetch_catalog(issue_catalogues[issue_date]), issue_date
                    )
                )
            except CommandError as exc:
                failures.append((issue_date.isoformat(), str(exc)))
                self.stderr.write(self.style.ERROR(str(exc)))
                if not options["continue_on_error"]:
                    raise

        if not options["skip_observed_tmax"] and not options["history_only"]:
            try:
                observed = self._discover_observed_tmax()
                if self._date_matches(observed["date"], options):
                    assets.append(observed)
            except CommandError as exc:
                failures.append(("observed-tmax", str(exc)))
                self.stderr.write(self.style.ERROR(str(exc)))
                if not options["continue_on_error"]:
                    raise

        if not assets:
            raise CommandError("No Heat and Thermal Stress images matched the options")

        self.stdout.write(f"Selected {len(assets)} image(s).")
        for asset in assets:
            self.stdout.write(
                f"{asset['date']} {asset['key']} {asset['source_url']}"
            )
        if options["inventory_only"]:
            if failures:
                raise CommandError(f"{len(failures)} source(s) were unavailable")
            return

        if options["dry_run"]:
            for asset in assets:
                existing = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                action = "REFRESH" if existing and options["refresh"] else (
                    "SKIP" if existing else "CREATE"
                )
                self.stdout.write(f"{action} {asset['date']} {asset['key']}")
            return

        product_page, item_types = self._get_or_create_destination(assets)
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        for asset in assets:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).first()
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_IMPORTED
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(f"SKIP {asset['key']} provenance #{existing.pk}")
                continue
            try:
                action = self._import_asset(
                    product_page, item_types[asset["key"]], asset, existing
                )
                counts[action] += 1
            except CommandError as exc:
                counts["failed"] += 1
                failures.append((asset["key"], str(exc)))
                self._record_failure(product_page, asset, existing, str(exc))
                self.stderr.write(self.style.ERROR(f"FAILED {asset['key']}: {exc}"))
                if not options["continue_on_error"]:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                "Heat and Thermal Stress migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(
                f"{len(failures)} source(s) failed: "
                + ", ".join(key for key, _ in failures)
            )

    def _discover_issue_catalogues(self, options):
        root_url = options["catalog_url"]
        direct_issues, year_catalogues = parse_catalog_references(
            self._fetch_catalog(root_url), root_url
        )
        issue_catalogues = direct_issues
        catalog_count = 1
        if options["include_history"] or options["history_only"]:
            for year, year_url in sorted(year_catalogues.items(), reverse=True):
                if options["from_date"] and year < options["from_date"].year:
                    continue
                if options["to_date"] and year > options["to_date"].year:
                    continue
                year_issues, _ = parse_catalog_references(
                    self._fetch_catalog(year_url), year_url
                )
                issue_catalogues.update(year_issues)
                catalog_count += 1
        return {
            issue_date: catalog_url
            for issue_date, catalog_url in issue_catalogues.items()
            if self._date_matches(issue_date, options)
        }, catalog_count

    @staticmethod
    def _date_matches(value, options):
        return not (
            (options["from_date"] and value < options["from_date"])
            or (options["to_date"] and value > options["to_date"])
        )

    @staticmethod
    def _fetch_catalog(catalog_url):
        try:
            response = requests.get(
                catalog_url,
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(
                f"Could not fetch THREDDS catalogue {catalog_url}: {exc}"
            ) from exc
        return response.content

    @staticmethod
    def _discover_observed_tmax():
        try:
            response = requests.head(
                OBSERVED_TMAX_URL,
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Could not inspect {OBSERVED_TMAX_URL}: {exc}") from exc
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
        if content_type not in {"image/jpeg", "image/jpg"}:
            raise CommandError(
                f"Observed Tmax returned {content_type or 'no MIME type'}"
            )
        modified_header = response.headers.get("Last-Modified")
        if not modified_header:
            raise CommandError("Observed Tmax has no Last-Modified header")
        try:
            modified = parsedate_to_datetime(modified_header)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                "Observed Tmax has an invalid Last-Modified header"
            ) from exc
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        modified = modified.astimezone(timezone.utc)
        return {
            "key": "observed-tmax",
            "name": "Observed Daily Maximum Temperature",
            "category": "Temperature Observations",
            "date": modified.date(),
            "valid_until": modified.date(),
            "filename": "Observed_Tmax.jpeg",
            "source_url": OBSERVED_TMAX_URL,
            "source_version": modified.isoformat(),
            "provenance_url": versioned_source_url(
                OBSERVED_TMAX_URL, modified.isoformat()
            ),
        }

    def _get_or_create_destination(self, assets):
        product, _ = Product.objects.get_or_create(
            name="Heat and Thermal Stress",
            defaults={
                "variable_name": "heat-and-thermal-stress",
                "temporal_resolution": "daily",
            },
        )
        item_types = {}
        categories = {}
        definitions = {asset["key"]: asset for asset in assets}
        for key, definition in definitions.items():
            category = categories.get(definition["category"])
            if not category:
                desired_format = "jpg" if key == "observed-tmax" else "png"
                category, _ = ProductCategory.objects.get_or_create(
                    product=product,
                    name=definition["category"],
                    defaults={
                        "icon": "temperature-high",
                        "category_format": desired_format,
                    },
                )
                if category.category_format != desired_format:
                    category.category_format = desired_format
                    category.save(update_fields=["category_format"])
                categories[definition["category"]] = category
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=definition["name"],
                defaults={
                    "file_name_convention": (
                        f"Heat_{key.replace('-', '_')}_{{yyyy}}{{mm}}{{dd}}"
                    ),
                    "valid_for_days": max(
                        1, (definition["valid_until"] - definition["date"]).days + 1
                    ),
                },
            )
            item_types[key] = item_type

        product_page = ProductPage.objects.filter(
            slug="heat-and-thermal-stress"
        ).first()
        if not product_page:
            index = ProductIndexPage.objects.live().first()
            if not index:
                raise CommandError("A live ProductIndexPage was not found")
            service = ServiceCategory.objects.filter(
                name="Weather Watch and Prediction"
            ).first()
            if not service:
                raise CommandError(
                    "Service category 'Weather Watch and Prediction' was not found"
                )
            product_page = ProductPage(
                title="Heat and Thermal Stress",
                slug="heat-and-thermal-stress",
                service=service,
                product=product,
                introduction_title="Heat and Thermal Stress",
                introduction_text=(
                    "Daily heat-index forecasts, persistent-hot-day indicators, "
                    "and maximum-temperature observations for Africa."
                ),
                products_per_page=7,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Heat and Thermal Stress ProductPage #{product_page.pk}"
                )
            )
        return product_page, item_types

    @staticmethod
    def _download_image(source_url):
        suffix = os.path.splitext(urlparse(source_url).path)[1] or ".img"
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            try:
                response = requests.get(
                    source_url,
                    timeout=(10, 120),
                    headers={"User-Agent": USER_AGENT},
                    allow_redirects=True,
                    stream=True,
                )
                response.raise_for_status()
                with temp:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > MAX_IMAGE_SIZE:
                            raise CommandError(
                                f"Image exceeds the 10 MiB limit: {source_url}"
                            )
                        digest.update(chunk)
                        temp.write(chunk)
            except requests.RequestException as exc:
                raise CommandError(f"Could not fetch {source_url}: {exc}") from exc
            with PillowImage.open(temp.name) as image:
                image.verify()
                if image.format not in {"PNG", "JPEG"}:
                    raise CommandError(f"Unsupported image format at {source_url}")
            return temp.name, digest.hexdigest()
        except Exception as exc:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Invalid image {source_url}: {exc}") from exc

    @staticmethod
    def _upsert_image_block(page, item_type, asset, image):
        raw = _get_products_raw(page)
        date_string = asset["date"].isoformat()
        for block in raw:
            value = block.get("value", {})
            if (
                block.get("type") == "image_product"
                and str(value.get("product_type")) == str(item_type.pk)
                and value.get("date") == date_string
            ):
                value["image"] = image.pk
                value["valid_until"] = asset["valid_until"].isoformat()
                _save_products_raw(page, raw)
                return
        _append_image_block(
            page,
            item_type.pk,
            asset["date"],
            image.pk,
            asset["valid_until"],
        )

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download_image(asset["source_url"])
        issue_date = asset["date"]
        page_title = f"Heat and Thermal Stress — {issue_date.isoformat()}"
        page_slug = f"heat-and-thermal-stress-{issue_date.isoformat()}"
        extension = (
            ".jpg"
            if asset["filename"].lower().endswith((".jpg", ".jpeg"))
            else ".png"
        )
        local_filename = (
            f"Heat_{asset['key'].replace('-', '_')}_"
            f"{issue_date.strftime('%Y%m%d')}{extension}"
        )
        media_title = f"{asset['name']} — {issue_date.isoformat()}"
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                current_import = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                if current_import and not existing:
                    self.stdout.write(f"SKIP {asset['key']} imported concurrently")
                    return "skipped"

                page = ProductItemPage.objects.child_of(product_page).filter(
                    slug=page_slug
                ).first()
                if not page:
                    page = ProductItemPage(
                        title=page_title,
                        slug=page_slug,
                        date=issue_date,
                        valid_until=asset["valid_until"],
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)

                Image = get_image_model()
                image = existing.image if existing and existing.image else None
                with open(temp_path, "rb") as handle:
                    if image:
                        image.title = media_title
                        image.file.save(local_filename, File(handle), save=True)
                    else:
                        image = Image(title=media_title)
                        image.file.save(local_filename, File(handle), save=True)

                self._upsert_image_block(page, item_type, asset, image)
                page.refresh_from_db()
                page.title = page_title
                page.date = issue_date
                if not page.valid_until or asset["valid_until"] > page.valid_until:
                    page.valid_until = asset["valid_until"]
                page.save_revision().publish()

                ProductSourceImport.objects.update_or_create(
                    source_url=asset["provenance_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": SOURCE_SYSTEM,
                        "source_published_date": issue_date,
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": existing.attempt_count + 1 if existing else 1,
                        "document": None,
                        "image": image,
                        "product_item_page": page,
                    },
                )
            action = "refreshed" if existing else "created"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action.upper()} {asset['key']} sha256={checksum[:12]}…"
                )
            )
            return action
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _record_failure(product_page, asset, existing, message):
        ProductSourceImport.objects.update_or_create(
            source_url=asset["provenance_url"],
            defaults={
                "product": product_page.product,
                "source_system": SOURCE_SYSTEM,
                "source_published_date": asset["date"],
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": None,
                "image": existing.image if existing else None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
