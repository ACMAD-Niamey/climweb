import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timedelta
from urllib.parse import quote, urljoin, urlparse, urlunparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from climweb.base.models import Product, ProductCategory, ProductItemType
from climweb.pages.products.management.commands.import_acmad_monthly_climate import (
    canonical_url,
    operational_url,
)
from climweb.pages.products.models import (
    ProductIndexPage,
    ProductItemPage,
    ProductPage,
    ProductSourceImport,
)
from climweb.pages.products.rcc import get_rcc_service_category
from climweb.pages.products.tasks import _append_image_block


DEFAULT_CATALOG_URL = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatemonitoringservice/Probability_of_Exceedance/5_Days/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD RCC 5-Day Rainfall Probability THREDDS"
THREDDS_NAMESPACE = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
FILENAME_PATTERN = re.compile(
    r"Probability_(?P<threshold>25|50|75|100|150)mm_5_Days(?P<day>[12])\.jpe?g$",
    re.I,
)
ISSUE_PATTERN = re.compile(r"^20\d{6}$")
THRESHOLDS = (25, 50, 75, 100, 150)
FORECAST_DAYS = (1, 2)
MAX_IMAGE_SIZE = 10 * 1024 * 1024
USER_AGENT = "ACMAD-ClimWeb-Five-Day-Rainfall-Importer/1.0"


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def parse_archive_catalog(xml_content, catalog_url):
    """Return dated child catalogues, excluding the mutable Current alias."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid THREDDS catalogue {catalog_url}: {exc}") from exc
    catalogs = []
    for ref in root.findall(f".//{{{THREDDS_NAMESPACE}}}catalogRef"):
        title = ref.get(f"{{{XLINK_NAMESPACE}}}title", "")
        href = ref.get(f"{{{XLINK_NAMESPACE}}}href")
        if not href or not ISSUE_PATTERN.fullmatch(title):
            continue
        catalogs.append(
            {
                "date": date.fromisoformat(
                    f"{title[:4]}-{title[4:6]}-{title[6:]}"
                ),
                "catalog_url": urljoin(catalog_url, href),
            }
        )
    return catalogs


def parse_issue_catalog(xml_content, catalog_url, issue_date):
    """Extract the ten threshold/day JPEG datasets from one dated catalogue."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid THREDDS catalogue {catalog_url}: {exc}") from exc
    parsed = urlparse(catalog_url)
    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath")
        match = FILENAME_PATTERN.fullmatch(filename)
        if not source_path or not match:
            continue
        threshold = int(match.group("threshold"))
        forecast_day = int(match.group("day"))
        source_url = urlunparse(
            parsed._replace(
                path="/thredds/fileServer/" + quote(source_path, safe="/"),
                query="",
                fragment="",
            )
        )
        assets.append(
            {
                "key": f"probability-{threshold}mm-day-{forecast_day}",
                "threshold": threshold,
                "forecast_day": forecast_day,
                "name": (
                    f"Probability of Exceeding {threshold} mm — "
                    f"Forecast Day {forecast_day}"
                ),
                "date": issue_date,
                "valid_until": issue_date + timedelta(days=5),
                "source_url": operational_url(source_url),
                "provenance_url": canonical_url(source_url),
            }
        )
    return assets


class Command(BaseCommand):
    help = "Import ACMAD RCC 5-day rainfall probability forecast maps."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--history-only", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--limit", type=int, default=3)
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--retry-failures", action="store_true")
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
        assets = self._discover_assets(
            options["catalog_url"],
            from_date=options["from_date"],
            to_date=options["to_date"],
            limit=options["limit"],
            oldest_first=options["oldest_first"],
        )
        grouped = {}
        for asset in assets:
            grouped.setdefault(asset["date"], []).append(asset)
        issue_dates = sorted(grouped, reverse=not options["oldest_first"])
        issue_dates = [
            issue_date for issue_date in issue_dates
            if not (options["from_date"] and issue_date < options["from_date"])
            and not (options["to_date"] and issue_date > options["to_date"])
        ][: options["limit"]]
        selected = [
            asset for issue_date in issue_dates for asset in grouped[issue_date]
        ]
        if not selected:
            raise CommandError(
                "No 5-day rainfall probability maps matched the selected options"
            )
        self.stdout.write(
            f"Selected {len(selected)} map(s) across "
            f"{len(issue_dates)} issue date(s)."
        )
        if options["inventory_only"] or options["dry_run"]:
            self._report_dry_run(selected, options["refresh"])
            return

        product_page, item_types = self._get_or_create_destination()
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        failures = []
        for asset in selected:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).first()
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_IMPORTED
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(f"SKIP {asset['date']} {asset['name']}")
                continue
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_FAILED
                and not options["retry_failures"]
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(f"SKIP {asset['date']} {asset['name']} failed")
                continue
            try:
                outcome = self._import_asset(
                    product_page, item_types[asset["key"]], asset, existing
                )
                counts[outcome] += 1
            except Exception as exc:
                counts["failed"] += 1
                failures.append(str(exc))
                self._record_failure(product_page, asset, existing, str(exc))
                self.stderr.write(f"FAILED {asset['date']} {asset['name']}: {exc}")
                if not options["continue_on_error"]:
                    raise
        self.stdout.write(
            "5-day rainfall import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if failures:
            raise CommandError(f"{len(failures)} 5-day rainfall map(s) failed")

    def _request(self, url, **kwargs):
        try:
            response = requests.get(
                operational_url(url), timeout=(10, 120),
                headers={"User-Agent": USER_AGENT}, allow_redirects=True, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _discover_assets(
        self,
        catalog_url,
        from_date=None,
        to_date=None,
        limit=None,
        oldest_first=False,
    ):
        catalogs = self._discover_catalogs(catalog_url)
        catalogs = [
            catalog
            for catalog in catalogs
            if not (from_date and catalog["date"] < from_date)
            and not (to_date and catalog["date"] > to_date)
        ]
        catalogs.sort(key=lambda catalog: catalog["date"], reverse=not oldest_first)
        if limit is not None:
            catalogs = catalogs[:limit]
        assets = []
        for catalog in catalogs:
            issue_url = canonical_url(catalog["catalog_url"])
            assets.extend(
                parse_issue_catalog(
                    self._request(issue_url).content, issue_url, catalog["date"]
                )
            )
        return assets

    def _discover_catalogs(self, catalog_url):
        root_url = canonical_url(catalog_url)
        return parse_archive_catalog(self._request(root_url).content, root_url)

    def _report_dry_run(self, assets, refresh):
        for asset in assets:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).exists()
            action = (
                "REFRESH"
                if existing and refresh
                else ("SKIP" if existing else "CREATE")
            )
            self.stdout.write(f"{action} {asset['date']} {asset['name']}")

    @staticmethod
    def _get_or_create_destination():
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="5-Day Rainfall Probability Forecast",
            defaults={
                "variable_name": "five-day-rainfall-probability-forecast",
                "temporal_resolution": "daily",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="five-day-rainfall-probability-forecast"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="5-Day Rainfall Probability Forecast",
                slug="five-day-rainfall-probability-forecast",
                service=service, product=product,
                introduction_title="5-Day Rainfall Probability Forecast",
                introduction_text=(
                    "Five-day rainfall forecast maps showing the probability of "
                    "exceeding 25, 50, 75, 100 and 150 mm for forecast days one "
                    "and two."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        elif product_page.service_id != service.pk:
            product_page.service = service
            product_page.save_revision().publish()
        category, _ = ProductCategory.objects.get_or_create(
            product=product, name="5-Day Rainfall Probability Maps",
            defaults={"icon": "heavy-rain", "category_format": "jpg"},
        )
        item_types = {}
        for threshold in THRESHOLDS:
            for forecast_day in FORECAST_DAYS:
                key = f"probability-{threshold}mm-day-{forecast_day}"
                item_type, _ = ProductItemType.objects.get_or_create(
                    category=category,
                    name=(
                        f"Probability of Exceeding {threshold} mm — "
                        f"Forecast Day {forecast_day}"
                    ),
                    defaults={
                        "file_name_convention": f"{key}_{{yyyy}}{{mm}}{{dd}}",
                        "valid_for_days": 5,
                    },
                )
                item_types[key] = item_type
        return product_page, item_types

    def _download(self, asset):
        response = self._request(asset["source_url"])
        if len(response.content) > MAX_IMAGE_SIZE:
            raise CommandError(f"Image exceeds the 10 MiB limit: {asset['source_url']}")
        temp = tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False)
        try:
            with temp:
                temp.write(response.content)
            with PillowImage.open(temp.name) as image:
                image.verify()
            return temp.name, hashlib.sha256(response.content).hexdigest()
        except Exception:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            raise

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        page_slug = f"five-day-rainfall-probability-{asset['date'].isoformat()}"
        display_date = asset["date"].strftime("%d %B %Y")
        page_title = f"5-Day Rainfall Probability Forecast — {display_date}"
        image_model = get_image_model()
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                page = (
                    ProductItemPage.objects.child_of(product_page)
                    .filter(slug=page_slug)
                    .first()
                )
                if not page:
                    page = ProductItemPage(
                        title=page_title,
                        slug=page_slug,
                        date=asset["date"],
                        valid_until=asset["valid_until"],
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)
                image = existing.image if existing and existing.image else None
                filename = f"{asset['key']}_{asset['date'].strftime('%Y%m%d')}.jpeg"
                with open(temp_path, "rb") as handle:
                    if image:
                        image.title = f"{asset['name']} — {display_date}"
                        image.file.save(filename, File(handle), save=True)
                    else:
                        image = image_model(title=f"{asset['name']} — {display_date}")
                        image.file.save(filename, File(handle), save=True)
                _append_image_block(
                    page,
                    item_type.pk,
                    asset["date"],
                    image.pk,
                    asset["valid_until"],
                )
                page.refresh_from_db()
                page.title = page_title
                page.date = asset["date"]
                page.valid_until = asset["valid_until"]
                page.save_revision().publish()
                ProductSourceImport.objects.update_or_create(
                    source_url=asset["provenance_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": SOURCE_SYSTEM,
                        "source_published_date": asset["date"],
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": existing.attempt_count + 1 if existing else 1,
                        "document": None,
                        "image": image,
                        "product_item_page": page,
                    },
                )
            outcome = "refreshed" if existing else "created"
            self.stdout.write(f"{outcome.upper()} {asset['date']} {asset['name']}")
            return outcome
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
                "checksum_sha256": "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message[:4000],
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": None,
                "image": existing.image if existing else None,
                "product_item_page": (
                    existing.product_item_page if existing else None
                ),
            },
        )
