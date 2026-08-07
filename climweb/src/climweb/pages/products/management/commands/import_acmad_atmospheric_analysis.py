import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timedelta, timezone
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


SOURCE_SYSTEM = "ACMAD Atmospheric Analysis THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Atmospheric-Analysis-Importer/1.0 (+https://new.acmad.org/)"
MAX_IMAGE_SIZE = 10 * 1024 * 1024
SOURCE_ROOT = "http://154.66.220.45:8080/thredds/fileServer/"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
HISTORY_CATALOGS = {
    "ncep": (
        "http://154.66.220.45:8080/thredds/catalog/ACMAD/CDD/"
        "ClimateBulletin_TN/NCEP_Clim_Next_Days/catalog.xml"
    ),
    "gfs": (
        "http://154.66.220.45:8080/thredds/catalog/ACMAD/CDD/"
        "DVP_FCST_PLOT/GFS/catalog.xml"
    ),
}

SOURCE_SPECS = (
    {
        "key": "climo-rh700",
        "collection": "ncep",
        "name": "5-day Relative Humidity and Wind at 700 hPa",
        "category": "5-day Atmospheric Climatology",
        "valid_for_days": 5,
        "filename": "ncep_climo_RH_Wnd_700_Africa_5days.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/ClimateBulletin_TN/NCEP_Clim_Next_Days/current/"
            "ncep_climo_RH_Wnd_700_Africa_5days.png"
        ),
    },
    {
        "key": "climo-rh850",
        "collection": "ncep",
        "name": "5-day Relative Humidity and Wind at 850 hPa",
        "category": "5-day Atmospheric Climatology",
        "valid_for_days": 5,
        "filename": "ncep_climo_RH_Wnd_850_Africa_5days.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/ClimateBulletin_TN/NCEP_Clim_Next_Days/current/"
            "ncep_climo_RH_Wnd_850_Africa_5days.png"
        ),
    },
    {
        "key": "climo-vorticity700",
        "collection": "ncep",
        "name": "5-day Vorticity and Wind at 700 hPa",
        "category": "5-day Atmospheric Climatology",
        "valid_for_days": 5,
        "filename": "ncep_climo_Vor_Wnd_WS_700_Africa_5days.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/ClimateBulletin_TN/NCEP_Clim_Next_Days/current/"
            "ncep_climo_Vor_Wnd_WS_700_Africa_5days.png"
        ),
    },
    {
        "key": "climo-vorticity850",
        "collection": "ncep",
        "name": "5-day Vorticity and Wind at 850 hPa",
        "category": "5-day Atmospheric Climatology",
        "valid_for_days": 5,
        "filename": "ncep_climo_Vor_Wnd_WS_850_Africa_5days.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/ClimateBulletin_TN/NCEP_Clim_Next_Days/current/"
            "ncep_climo_Vor_Wnd_WS_850_Africa_5days.png"
        ),
    },
    {
        "key": "climo-z500",
        "collection": "ncep",
        "name": "5-day 500 hPa Geopotential",
        "category": "5-day Atmospheric Climatology",
        "valid_for_days": 5,
        "filename": "ncep_climo_Z500_Africa_5days.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/ClimateBulletin_TN/NCEP_Clim_Next_Days/current/"
            "ncep_climo_Z500_Africa_5days.png"
        ),
    },
    {
        "key": "gfs-mslp-anomaly",
        "collection": "gfs",
        "name": "GFS Mean Sea-level Pressure Anomaly",
        "category": "Daily Synoptic Analysis",
        "valid_for_days": 1,
        "filename": "gfs_MSLP_Anom_Africa_init_D0-00_daily.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/DVP_FCST_PLOT/GFS/current/"
            "gfs_MSLP_Anom_Africa_init_D0-00_daily.png"
        ),
    },
    {
        "key": "gfs-integrated-rh",
        "collection": "gfs",
        "name": "GFS Integrated Relative Humidity 925–700 hPa",
        "category": "Daily Synoptic Analysis",
        "valid_for_days": 1,
        "filename": "gfs_Int_RH_W925_W700_Africa_init_D0-00_for_dly_12.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/DVP_FCST_PLOT/GFS/current/"
            "gfs_Int_RH_W925_W700_Africa_init_D0-00_for_dly_12.png"
        ),
    },
    {
        "key": "gfs-integrated-vorticity",
        "collection": "gfs",
        "name": "GFS Integrated Vorticity and Wind 925–600 hPa",
        "category": "Daily Synoptic Analysis",
        "valid_for_days": 1,
        "filename": "gfs_Int_Vor_Wnd_WS_Africa_init_D0-00_for_dly_12.png",
        "source_url": (
            SOURCE_ROOT
            + "ACMAD/CDD/DVP_FCST_PLOT/GFS/current/"
            "gfs_Int_Vor_Wnd_WS_Africa_init_D0-00_for_dly_12.png"
        ),
    },
)


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def versioned_source_url(source_url, source_version):
    parsed = urlparse(source_url)
    return urlunparse(
        parsed._replace(query=urlencode({"acmad_version": source_version}))
    )


def parse_history_root_catalog(xml_content, catalog_url):
    """Return issue dates and child catalogue URLs from a THREDDS root."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(
            f"Invalid THREDDS catalogue {catalog_url}: {exc}"
        ) from exc

    catalogues = {}
    title_key = f"{{{XLINK_NAMESPACE}}}title"
    href_key = f"{{{XLINK_NAMESPACE}}}href"
    for reference in root.findall(f".//{{{THREDDS_NAMESPACE}}}catalogRef"):
        title = reference.get(title_key, "")
        if not re.fullmatch(r"20\d{6}", title):
            continue
        try:
            issue_date = date(
                int(title[0:4]), int(title[4:6]), int(title[6:8])
            )
        except ValueError:
            continue
        href = reference.get(href_key)
        if href:
            catalogues[issue_date] = urljoin(catalog_url, href)
    return catalogues


def parse_history_issue_catalog(xml_content, issue_date, specs):
    """Extract only the exact pilot files from a dated THREDDS catalogue."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(
            f"Invalid THREDDS issue catalogue for {issue_date}: {exc}"
        ) from exc

    specs_by_filename = {spec["filename"]: spec for spec in specs}
    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        spec = specs_by_filename.get(filename)
        source_path = dataset.get("urlPath")
        if not spec or not source_path:
            continue
        modified_element = dataset.find(f"{{{THREDDS_NAMESPACE}}}date")
        source_version = (
            modified_element.text.strip()
            if modified_element is not None and modified_element.text
            else issue_date.isoformat()
        )
        source_url = SOURCE_ROOT + quote(source_path.lstrip("/"), safe="/")
        assets.append(
            {
                **spec,
                "date": issue_date,
                "source_url": source_url,
                "source_version": source_version,
                "provenance_url": versioned_source_url(
                    source_url, source_version
                ),
            }
        )
    return assets


class Command(BaseCommand):
    help = "Import current or historical ACMAD Atmospheric Analysis PNG products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            action="append",
            choices=[spec["key"] for spec in SOURCE_SPECS],
            help="Import only the selected source key. This option may be repeated.",
        )
        parser.add_argument(
            "--issue-date",
            type=iso_date,
            help="Override the issue date inferred from Last-Modified headers.",
        )
        parser.add_argument(
            "--include-history",
            action="store_true",
            help="Also discover and import dated archive folders.",
        )
        parser.add_argument(
            "--history-only",
            action="store_true",
            help="Import dated archive folders without importing current files.",
        )
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument(
            "--limit",
            dest="history_limit",
            type=int,
            default=3,
            help="Maximum historical issue dates to inspect (default: 3).",
        )
        parser.add_argument(
            "--oldest-first",
            action="store_true",
            help="Select the oldest matching historical dates first.",
        )
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        history_requested = options["include_history"] or options["history_only"]
        if (options["from_date"] or options["to_date"]) and not history_requested:
            raise CommandError(
                "--from-date and --to-date require --include-history or --history-only"
            )
        if options["issue_date"] and history_requested:
            raise CommandError(
                "--issue-date cannot be combined with historical imports"
            )
        if options["history_limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if (
            options["from_date"]
            and options["to_date"]
            and options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        selected_keys = set(options["source"] or [])
        specs = [
            spec
            for spec in SOURCE_SPECS
            if not selected_keys or spec["key"] in selected_keys
        ]
        assets = []
        discovery_failures = []
        if not options["history_only"]:
            current_assets, current_failures = self._discover_current(
                specs, options["issue_date"], options["continue_on_error"]
            )
            assets.extend(current_assets)
            discovery_failures.extend(current_failures)

        if history_requested:
            history_assets, history_failures = self._discover_history(
                specs, options
            )
            current_dates = {
                asset["date"]
                for asset in assets
                if "/current/" in asset["source_url"]
            }
            if not options["history_only"]:
                history_assets = [
                    asset
                    for asset in history_assets
                    if asset["date"] not in current_dates
                ]
            assets.extend(history_assets)
            discovery_failures.extend(history_failures)

        if not assets:
            raise CommandError("No Atmospheric Analysis sources were available")

        issue_dates = sorted({asset["date"] for asset in assets}, reverse=True)
        self.stdout.write(
            f"Selected {len(assets)} PNG source(s) across {len(issue_dates)} "
            f"issue date(s)."
        )
        for asset in assets:
            self.stdout.write(
                f"{asset['date']} {asset['key']} {asset['source_url']}"
            )
        if options["inventory_only"]:
            if discovery_failures:
                raise CommandError(
                    f"{len(discovery_failures)} source(s) were unavailable"
                )
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

        product_page, item_types = self._get_or_create_destination()
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        failures = list(discovery_failures)
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
                "Atmospheric Analysis migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(
                f"{len(failures)} source(s) failed: "
                + ", ".join(key for key, _ in failures)
            )

    def _discover_current(self, specs, issue_date_override, continue_on_error):
        assets = []
        failures = []
        for spec in specs:
            try:
                source_date, source_version = self._source_metadata(
                    spec["source_url"]
                )
            except CommandError as exc:
                failures.append((spec["key"], str(exc)))
                self.stderr.write(
                    self.style.ERROR(f"UNAVAILABLE {spec['key']}: {exc}")
                )
                if not continue_on_error:
                    raise
                continue
            issue_date = issue_date_override or source_date
            assets.append(
                {
                    **spec,
                    "date": issue_date,
                    "source_version": source_version,
                    "provenance_url": versioned_source_url(
                        spec["source_url"], source_version
                    ),
                }
            )
        return assets, failures

    def _discover_history(self, specs, options):
        collections = {spec["collection"] for spec in specs}
        root_catalogues = {}
        failures = []
        for collection in sorted(collections):
            catalog_url = HISTORY_CATALOGS[collection]
            try:
                root_catalogues[collection] = parse_history_root_catalog(
                    self._fetch_catalog(catalog_url), catalog_url
                )
            except CommandError as exc:
                failures.append((f"{collection}-history", str(exc)))
                self.stderr.write(self.style.ERROR(str(exc)))
                if not options["continue_on_error"]:
                    raise

        dates = set()
        for catalogues in root_catalogues.values():
            dates.update(catalogues)
        if options["from_date"]:
            dates = {value for value in dates if value >= options["from_date"]}
        if options["to_date"]:
            dates = {value for value in dates if value <= options["to_date"]}
        selected_dates = sorted(dates, reverse=not options["oldest_first"])[
            : options["history_limit"]
        ]
        self.stdout.write(
            f"Historical discovery found {len(dates)} matching issue date(s); "
            f"inspecting {len(selected_dates)}."
        )

        assets = []
        for issue_date in selected_dates:
            for collection in sorted(collections):
                catalog_url = root_catalogues.get(collection, {}).get(issue_date)
                if not catalog_url:
                    continue
                collection_specs = [
                    spec for spec in specs if spec["collection"] == collection
                ]
                try:
                    assets.extend(
                        parse_history_issue_catalog(
                            self._fetch_catalog(catalog_url),
                            issue_date,
                            collection_specs,
                        )
                    )
                except CommandError as exc:
                    key = f"{collection}-{issue_date.isoformat()}"
                    failures.append((key, str(exc)))
                    self.stderr.write(self.style.ERROR(str(exc)))
                    if not options["continue_on_error"]:
                        raise
        return assets, failures

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
    def _source_metadata(source_url):
        try:
            response = requests.head(
                source_url,
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Could not inspect {source_url}: {exc}") from exc

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
        if content_type != "image/png":
            raise CommandError(
                f"Expected image/png metadata from {source_url}, got "
                f"{content_type or 'an empty Content-Type'}"
            )
        last_modified = response.headers.get("Last-Modified")
        if not last_modified:
            raise CommandError(f"No Last-Modified date was provided for {source_url}")
        try:
            modified = parsedate_to_datetime(last_modified)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                f"Invalid Last-Modified date {last_modified!r} for {source_url}"
            ) from exc
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        modified = modified.astimezone(timezone.utc)
        return modified.date(), modified.isoformat()

    def _get_or_create_destination(self):
        product, _ = Product.objects.get_or_create(
            name="Atmospheric Analysis",
            defaults={
                "variable_name": "atmospheric-analysis",
                "temporal_resolution": "daily",
            },
        )
        changed_fields = []
        if not product.variable_name:
            product.variable_name = "atmospheric-analysis"
            changed_fields.append("variable_name")
        if not product.temporal_resolution:
            product.temporal_resolution = "daily"
            changed_fields.append("temporal_resolution")
        if changed_fields:
            product.save(update_fields=changed_fields)

        categories = {}
        item_types = {}
        for spec in SOURCE_SPECS:
            category = categories.get(spec["category"])
            if not category:
                category, _ = ProductCategory.objects.get_or_create(
                    product=product,
                    name=spec["category"],
                    defaults={"icon": "map", "category_format": "png"},
                )
                categories[spec["category"]] = category
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=spec["name"],
                defaults={
                    "file_name_convention": (
                        f"Atmospheric_{spec['key'].replace('-', '_')}_"
                        "{yyyy}{mm}{dd}"
                    ),
                    "valid_for_days": spec["valid_for_days"],
                },
            )
            item_types[spec["key"]] = item_type

        product_page = ProductPage.objects.filter(slug="atmospheric-analysis").first()
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
                title="Atmospheric Analysis",
                slug="atmospheric-analysis",
                service=service,
                product=product,
                introduction_title="Atmospheric Analysis",
                introduction_text=(
                    "Current synoptic analysis and short-range atmospheric "
                    "climatology maps for Africa, including pressure, humidity, "
                    "wind, vorticity, and geopotential fields."
                ),
                products_per_page=7,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Atmospheric Analysis ProductPage #{product_page.pk}"
                )
            )
        return product_page, item_types

    @staticmethod
    def _download_image(source_url):
        temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
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
                if image.format != "PNG":
                    raise CommandError(
                        f"Source did not return a PNG image: {source_url}"
                    )
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
        valid_until = (
            asset["date"] + timedelta(days=asset["valid_for_days"] - 1)
        )
        for block in raw:
            value = block.get("value", {})
            if (
                block.get("type") == "image_product"
                and str(value.get("product_type")) == str(item_type.pk)
                and value.get("date") == date_string
            ):
                value["image"] = image.pk
                value["valid_until"] = valid_until.isoformat()
                _save_products_raw(page, raw)
                return
        _append_image_block(
            page, item_type.pk, asset["date"], image.pk, valid_until
        )

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download_image(asset["source_url"])
        issue_date = asset["date"]
        asset_valid_until = issue_date + timedelta(
            days=asset["valid_for_days"] - 1
        )
        page_title = f"Atmospheric Analysis — {issue_date.isoformat()}"
        page_slug = f"atmospheric-analysis-{issue_date.isoformat()}"
        local_filename = (
            f"Atmospheric_{asset['key'].replace('-', '_')}_"
            f"{issue_date.strftime('%Y%m%d')}.png"
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
                        valid_until=asset_valid_until,
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
                if not page.valid_until or asset_valid_until > page.valid_until:
                    page.valid_until = asset_valid_until
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
