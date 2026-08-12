import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse, urlunparse

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
    "climatemonitoringservice/Probability_of_Exceedance/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD RCC Rainfall Exceedance THREDDS"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
FILENAME_PATTERN = re.compile(r"Excedence(?P<threshold>\d{3,4})mm\.jpe?g$", re.I)
THRESHOLDS = tuple(range(100, 1001, 100))
MAX_IMAGE_SIZE = 10 * 1024 * 1024
USER_AGENT = "ACMAD-ClimWeb-Rainfall-Exceedance-Importer/1.0"


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def header_date(headers):
    value = headers.get("Last-Modified")
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.date()


def parse_catalog(xml_content, catalog_url):
    """Extract the ten seasonal-total threshold JPEG datasets."""
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
        if threshold not in THRESHOLDS:
            continue
        source_url = urlunparse(
            parsed._replace(
                path="/thredds/fileServer/" + quote(source_path, safe="/"),
                query="",
                fragment="",
            )
        )
        assets.append(
            {
                "key": f"exceedance-{threshold}mm",
                "threshold": threshold,
                "name": f"Probability of Exceeding {threshold} mm",
                "source_url": operational_url(source_url),
                "provenance_url": canonical_url(source_url),
            }
        )
    return assets


class Command(BaseCommand):
    help = "Import ACMAD RCC seasonal rainfall probability-of-exceedance maps."

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
        if options["from_date"] and options["to_date"] and (
            options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        assets = self._discover_assets(options["catalog_url"])
        grouped = {}
        for asset in assets:
            grouped.setdefault(asset["date"], []).append(asset)
        issue_dates = sorted(grouped, reverse=not options["oldest_first"])
        issue_dates = [
            issue_date
            for issue_date in issue_dates
            if not (options["from_date"] and issue_date < options["from_date"])
            and not (options["to_date"] and issue_date > options["to_date"])
        ][: options["limit"]]
        selected = [
            asset
            for issue_date in issue_dates
            for asset in grouped[issue_date]
        ]
        if not selected:
            raise CommandError(
                "No rainfall exceedance maps matched the selected options"
            )

        self.stdout.write(
            f"Selected {len(selected)} map(s) across {len(issue_dates)} issue date(s)."
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
            "Rainfall exceedance import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if failures:
            raise CommandError(f"{len(failures)} rainfall exceedance map(s) failed")

    def _request(self, url, method="get", **kwargs):
        try:
            request = requests.head if method == "head" else requests.get
            response = request(
                operational_url(url),
                timeout=(10, 120),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _discover_assets(self, catalog_url):
        canonical_catalog = canonical_url(catalog_url)
        assets = parse_catalog(
            self._request(canonical_catalog).content,
            canonical_catalog,
        )
        for asset in assets:
            metadata = self._request(asset["source_url"], method="head")
            issue_date = header_date(metadata.headers)
            if not issue_date:
                raise CommandError(f"No Last-Modified date for {asset['source_url']}")
            asset["date"] = issue_date
            asset["valid_until"] = issue_date + timedelta(days=3650)
        return assets

    def _report_dry_run(self, assets, refresh):
        for asset in assets:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).exists()
            action = "REFRESH" if existing and refresh else (
                "SKIP" if existing else "CREATE"
            )
            self.stdout.write(f"{action} {asset['date']} {asset['name']}")

    @staticmethod
    def _get_or_create_destination():
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Seasonal Rainfall Probability of Exceedance",
            defaults={
                "variable_name": "seasonal-rainfall-probability-of-exceedance",
                "temporal_resolution": "seasonal",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="seasonal-rainfall-probability-of-exceedance"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Seasonal Rainfall Probability of Exceedance",
                slug="seasonal-rainfall-probability-of-exceedance",
                service=service,
                product=product,
                introduction_title="Seasonal Rainfall Probability of Exceedance",
                introduction_text=(
                    "Probability maps showing where seasonal total precipitation "
                    "is expected to exceed thresholds from 100 to 1000 mm."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        elif product_page.service_id != service.pk:
            product_page.service = service
            product_page.save_revision().publish()

        category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Seasonal Total Precipitation Exceedance",
            defaults={"icon": "heavy-rain", "category_format": "jpg"},
        )
        item_types = {}
        for threshold in THRESHOLDS:
            key = f"exceedance-{threshold}mm"
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=f"Probability of Exceeding {threshold} mm",
                defaults={
                    "file_name_convention": f"{key}_{{yyyy}}{{mm}}{{dd}}",
                    "valid_for_days": 3650,
                },
            )
            item_types[key] = item_type
        return product_page, item_types

    def _download(self, asset):
        response = self._request(asset["source_url"])
        if len(response.content) > MAX_IMAGE_SIZE:
            raise CommandError(
                f"Image exceeds the 10 MiB limit: {asset['source_url']}"
            )
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
        page_slug = f"seasonal-rainfall-exceedance-{asset['date'].isoformat()}"
        display_date = asset["date"].strftime("%d %B %Y")
        page_title = f"Seasonal Rainfall Probability of Exceedance — {display_date}"
        image_model = get_image_model()
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                page = ProductItemPage.objects.child_of(product_page).filter(
                    slug=page_slug
                ).first()
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
                    page, item_type.pk, asset["date"], image.pk, asset["valid_until"]
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
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
