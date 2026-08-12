import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, datetime, timedelta, timezone
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
    "https://sgbd.acmad.org/thredds/catalog/FIT/SATELLITE/catalog.xml"
)
FILE_SERVER_ROOT = "https://sgbd.acmad.org/thredds/fileServer/"
IR_ARCHIVE_CATALOG = (
    "https://sgbd.acmad.org/thredds/catalog/FIT/SATELLITE/IR_108/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD Satellite THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Nowcasting-Importer/1.0 (+https://new.acmad.org/)"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
MAX_IMAGE_SIZE = 10 * 1024 * 1024

CHANNELS = (
    {
        "key": "infrared-108",
        "code": "IR_108",
        "current": "IR_108.jpg",
        "name": "Infrared 10.8 µm Satellite Image",
    },
    {
        "key": "colour-composite",
        "code": "CC",
        "current": "CC.jpg",
        "name": "Colour Composite Satellite Image",
    },
    {
        "key": "day-night-cloud",
        "code": "CC_DNC",
        "current": "CC_DNC.jpg",
        "name": "Day/Night Cloud Microphysics RGB",
    },
    {
        "key": "airmass-rgb",
        "code": "CC_AIRMASS",
        "current": "CC_AIRMASS.jpg",
        "name": "Airmass RGB Satellite Image",
    },
)
CHANNELS_BY_CURRENT = {channel["current"]: channel for channel in CHANNELS}
ARCHIVE_IMAGE = re.compile(r"^IR_108\.(20\d{12})\.jpg$", re.I)
YEAR_REFERENCE = re.compile(r"^IR_108_(20\d{2})$")
MONTH_REFERENCE = re.compile(r"^IR_108_(20\d{4})$")


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def compact_datetime(value):
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid compact timestamp {value!r}") from exc


def operational_url(source_url):
    """Use ACMAD's HTTP THREDDS port because its legacy TLS is rejected."""
    parsed = urlparse(source_url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def versioned_source_url(source_url, source_version):
    parsed = urlparse(source_url)
    return urlunparse(
        parsed._replace(query=urlencode({"acmad_version": source_version}))
    )


def parse_references(xml_content, catalog_url):
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid satellite THREDDS catalogue: {exc}") from exc
    references = []
    for reference in root.findall(f".//{{{THREDDS_NAMESPACE}}}catalogRef"):
        title = reference.get(f"{{{XLINK_NAMESPACE}}}title", "")
        href = reference.get(f"{{{XLINK_NAMESPACE}}}href")
        if href:
            references.append((title, urljoin(catalog_url, href)))
    return references


def parse_current_catalog(xml_content):
    """Select the four audited fixed-name satellite JPEGs."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid satellite THREDDS catalogue: {exc}") from exc

    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath")
        channel = CHANNELS_BY_CURRENT.get(filename)
        if not channel or not source_path:
            continue
        modified_node = dataset.find(f"{{{THREDDS_NAMESPACE}}}date")
        if modified_node is None or not modified_node.text:
            continue
        try:
            modified = datetime.fromisoformat(
                modified_node.text.strip().replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError:
            continue
        issue_time = (modified - timedelta(minutes=15)).replace(
            second=0, microsecond=0
        )
        source_url = FILE_SERVER_ROOT + quote(source_path.lstrip("/"), safe="/")
        assets.append(
            {
                **channel,
                "issue_time": issue_time,
                "filename": filename,
                "source_url": source_url,
                "provenance_url": versioned_source_url(
                    source_url, modified.isoformat()
                ),
                "is_current": True,
            }
        )
    if assets:
        group_time = max(asset["issue_time"] for asset in assets)
        for asset in assets:
            asset["issue_time"] = group_time
    return assets


def parse_ir_archive_catalog(xml_content):
    """Return timestamped IR archive entries used to construct all channels."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid IR archive catalogue: {exc}") from exc

    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        match = ARCHIVE_IMAGE.fullmatch(filename)
        if not match:
            continue
        try:
            issue_time = compact_datetime(match.group(1))
        except ValueError:
            continue
        year = issue_time.strftime("%Y")
        month = issue_time.strftime("%Y%m")
        timestamp = issue_time.strftime("%Y%m%d%H%M%S")
        for channel in CHANNELS:
            archive_filename = f"{channel['code']}.{timestamp}.jpg"
            source_path = (
                f"FIT/SATELLITE/{channel['code']}/{channel['code']}_{year}/"
                f"{channel['code']}_{month}/{archive_filename}"
            )
            source_url = FILE_SERVER_ROOT + source_path
            assets.append(
                {
                    **channel,
                    "issue_time": issue_time,
                    "filename": archive_filename,
                    "source_url": source_url,
                    "provenance_url": source_url,
                    "is_current": False,
                }
            )
    return assets


class Command(BaseCommand):
    help = "Import current or historical ACMAD nowcasting satellite JPEGs."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument(
            "--ir-archive-catalog", default=IR_ARCHIVE_CATALOG
        )
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--history-only", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--limit", type=int, default=3)
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if options["from_date"] and options["to_date"] and (
            options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        assets = []
        if not options["history_only"]:
            assets.extend(
                parse_current_catalog(self._get(options["catalog_url"]).content)
            )
        if options["include_history"] or options["history_only"]:
            assets.extend(self._discover_history(options))
        assets = [
            asset
            for asset in assets
            if self._date_matches(asset["issue_time"].date(), options)
        ]
        assets_by_identity = {}
        for asset in assets:
            identity = (asset["issue_time"], asset["key"])
            current = assets_by_identity.get(identity)
            if not current or (asset["is_current"] and not current["is_current"]):
                assets_by_identity[identity] = asset
        assets = list(assets_by_identity.values())

        issue_times = sorted(
            {asset["issue_time"] for asset in assets},
            reverse=not options["oldest_first"],
        )[: options["limit"]]
        assets = [asset for asset in assets if asset["issue_time"] in issue_times]
        assets.sort(
            key=lambda asset: (
                asset["issue_time"]
                if options["oldest_first"]
                else -asset["issue_time"].timestamp(),
                asset["key"],
            )
        )
        if not assets:
            raise CommandError("No nowcasting satellite images matched the options")

        self.stdout.write(
            f"Selected {len(assets)} image(s) across "
            f"{len(issue_times)} issue time(s)."
        )
        for asset in assets:
            self.stdout.write(
                f"{asset['issue_time'].isoformat()} {asset['key']} "
                f"{asset['source_url']}"
            )
        if options["inventory_only"]:
            return
        if options["dry_run"]:
            for asset in assets:
                existing = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                action = "REFRESH" if existing and options["refresh"] else (
                    "SKIP" if existing else "CREATE"
                )
                self.stdout.write(
                    f"{action} {asset['issue_time'].isoformat()} {asset['key']}"
                )
            return

        product_page, item_types = self._get_or_create_destination()
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        failures = []
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
                continue
            try:
                action = self._import_asset(
                    product_page, item_types[asset["key"]], asset, existing
                )
                counts[action] += 1
            except CommandError as exc:
                counts["failed"] += 1
                failures.append((asset, str(exc)))
                self._record_failure(product_page, asset, existing, str(exc))
                self.stderr.write(self.style.ERROR(f"FAILED {asset['key']}: {exc}"))
                if not options["continue_on_error"]:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                "Thunderstorm and Nowcasting migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(f"{len(failures)} nowcasting image(s) failed")

    def _discover_history(self, options):
        archive_root = options["ir_archive_catalog"]
        year_references = {
            int(match.group(1)): url
            for title, url in parse_references(
                self._get(archive_root).content, archive_root
            )
            if (match := YEAR_REFERENCE.fullmatch(title))
        }
        years = sorted(year_references, reverse=not options["oldest_first"])
        if options["from_date"]:
            years = [year for year in years if year >= options["from_date"].year]
        if options["to_date"]:
            years = [year for year in years if year <= options["to_date"].year]
        if not options["from_date"] and not options["to_date"]:
            years = years[:1]

        assets = []
        for year in years:
            year_url = year_references[year]
            month_references = {
                int(match.group(1)): url
                for title, url in parse_references(
                    self._get(year_url).content, year_url
                )
                if (match := MONTH_REFERENCE.fullmatch(title))
            }
            months = sorted(
                month_references, reverse=not options["oldest_first"]
            )
            if options["from_date"]:
                minimum = options["from_date"].year * 100 + options["from_date"].month
                months = [month for month in months if month >= minimum]
            if options["to_date"]:
                maximum = options["to_date"].year * 100 + options["to_date"].month
                months = [month for month in months if month <= maximum]
            if not options["from_date"] and not options["to_date"]:
                months = months[:1]
            for month in months:
                assets.extend(
                    parse_ir_archive_catalog(
                        self._get(month_references[month]).content
                    )
                )
        return assets

    @staticmethod
    def _date_matches(value, options):
        return not (
            (options["from_date"] and value < options["from_date"])
            or (options["to_date"] and value > options["to_date"])
        )

    @staticmethod
    def _get(url, **kwargs):
        try:
            response = requests.get(
                operational_url(url),
                timeout=(10, 90),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    @staticmethod
    def _get_or_create_destination():
        product, _ = Product.objects.get_or_create(
            name="Thunderstorm and Nowcasting",
            defaults={
                "variable_name": "thunderstorm-and-nowcasting",
                "temporal_resolution": "hourly",
            },
        )
        category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Satellite Imagery",
            defaults={"icon": "cloud-sun", "category_format": "jpg"},
        )
        item_types = {}
        for channel in CHANNELS:
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=channel["name"],
                defaults={
                    "file_name_convention": (
                        f"Nowcasting_{channel['code']}_"
                        "{yyyy}{mm}{dd}{hh}"
                    ),
                    "valid_for_days": 1,
                },
            )
            item_types[channel["key"]] = item_type

        product_page = ProductPage.objects.filter(
            slug="thunderstorm-and-nowcasting"
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
                title="Thunderstorm and Nowcasting",
                slug="thunderstorm-and-nowcasting",
                service=service,
                product=product,
                introduction_title="Thunderstorm and Nowcasting",
                introduction_text=(
                    "Near-real-time infrared and RGB satellite imagery supporting "
                    "thunderstorm monitoring and operational nowcasting over Africa."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        return product_page, item_types

    @staticmethod
    def _download_image(source_url):
        temp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            response = Command._get(source_url, stream=True)
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
            with PillowImage.open(temp.name) as image:
                image.verify()
                if image.format != "JPEG":
                    raise CommandError(f"Source did not return a JPEG: {source_url}")
            return temp.name, digest.hexdigest()
        except Exception as exc:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Invalid image {source_url}: {exc}") from exc

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download_image(asset["source_url"])
        issue_time = asset["issue_time"]
        issue_date = issue_time.date()
        time_label = issue_time.strftime("%Y-%m-%d %H:%M UTC")
        slug_timestamp = issue_time.strftime("%Y-%m-%d-%H%M")
        page_slug = f"thunderstorm-and-nowcasting-{slug_timestamp}"
        page_title = f"Thunderstorm and Nowcasting — {time_label}"
        media_title = f"{asset['name']} — {time_label}"
        filename = (
            f"Nowcasting_{asset['code']}_{issue_time.strftime('%Y%m%d%H%M')}.jpg"
        )
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                concurrent = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                if concurrent and not existing:
                    return "skipped"
                page = (
                    ProductItemPage.objects.child_of(product_page)
                    .filter(slug=page_slug)
                    .first()
                )
                if not page:
                    page = ProductItemPage(
                        title=page_title,
                        slug=page_slug,
                        date=issue_date,
                        valid_until=issue_date,
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)

                Image = get_image_model()
                image = (
                    existing.image
                    if existing and existing.image
                    else Image(title=media_title)
                )
                with open(temp_path, "rb") as handle:
                    image.title = media_title
                    image.file.save(filename, File(handle), save=True)
                self._upsert_image_block(page, item_type, asset, image)
                page.refresh_from_db()
                page.title = page_title
                page.date = issue_date
                page.valid_until = issue_date
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
            return "refreshed" if existing else "created"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _upsert_image_block(page, item_type, asset, image):
        raw = _get_products_raw(page)
        date_string = asset["issue_time"].date().isoformat()
        for block in raw:
            value = block.get("value", {})
            if (
                block.get("type") == "image_product"
                and str(value.get("product_type")) == str(item_type.pk)
                and value.get("date") == date_string
            ):
                value["image"] = image.pk
                _save_products_raw(page, raw)
                return
        _append_image_block(
            page,
            item_type.pk,
            asset["issue_time"].date(),
            image.pk,
            asset["issue_time"].date(),
        )

    @staticmethod
    def _record_failure(product_page, asset, existing, message):
        ProductSourceImport.objects.update_or_create(
            source_url=asset["provenance_url"],
            defaults={
                "product": product_page.product,
                "source_system": SOURCE_SYSTEM,
                "source_published_date": asset["issue_time"].date(),
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": None,
                "image": existing.image if existing else None,
                "product_item_page": (
                    existing.product_item_page if existing else None
                ),
            },
        )
