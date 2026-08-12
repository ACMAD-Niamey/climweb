import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timedelta
from urllib.parse import quote, urlparse, urlunparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from climweb.base.models import Product, ProductCategory, ProductItemType
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
    "climatemonitoringservice/Onset_Ops_Services/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD RCC Season Onset THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Season-Onset-Importer/1.0 (+https://new.acmad.org/)"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
MAX_IMAGE_SIZE = 20 * 1024 * 1024
ASSET_PATTERN = re.compile(
    r"^ecowas_Seasonal_Onset_(?P<kind>Obs|Fcst)_"
    r"(?P<date>20\d{6})\.jpe?g$",
    re.IGNORECASE,
)
PRODUCT_TYPES = {
    "observed-onset": "Observed Season Onset",
    "forecast-onset": "Forecast Season Onset",
}


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


def canonical_url(url):
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="https", netloc="sgbd.acmad.org")
    return urlunparse(parsed)


def operational_url(url):
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def parse_catalog(xml_content, catalog_url=DEFAULT_CATALOG_URL):
    """Extract the audited observed and forecast onset JPEGs."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid season-onset THREDDS catalogue: {exc}") from exc

    parsed_catalog = urlparse(canonical_url(catalog_url))
    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath")
        match = ASSET_PATTERN.fullmatch(filename)
        if not source_path or not match:
            continue
        try:
            issue_date = compact_date(match.group("date"))
        except ValueError:
            continue
        key = (
            "observed-onset"
            if match.group("kind").lower() == "obs"
            else "forecast-onset"
        )
        source_url = urlunparse(
            parsed_catalog._replace(
                path="/thredds/fileServer/" + quote(source_path, safe="/"),
                query="",
                fragment="",
            )
        )
        assets.append({
            "key": key,
            "name": PRODUCT_TYPES[key],
            "date": issue_date,
            "valid_until": issue_date + timedelta(days=4),
            "filename": filename,
            "source_url": canonical_url(source_url),
            "provenance_url": canonical_url(source_url),
        })
    return assets


class Command(BaseCommand):
    help = "Import current or historical ACMAD RCC season-onset JPEG maps."

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

        assets = parse_catalog(
            self._request(options["catalog_url"]).content,
            options["catalog_url"],
        )
        assets = [
            asset
            for asset in assets
            if not (
                options["from_date"] and asset["date"] < options["from_date"]
            )
            and not (options["to_date"] and asset["date"] > options["to_date"])
        ]
        issue_dates = sorted(
            {asset["date"] for asset in assets},
            reverse=not options["oldest_first"],
        )[: options["limit"]]
        assets = [asset for asset in assets if asset["date"] in issue_dates]
        assets.sort(
            key=lambda asset: (
                asset["date"]
                if options["oldest_first"]
                else -asset["date"].toordinal(),
                asset["key"],
            )
        )
        if not assets:
            raise CommandError("No season-onset maps matched the selected options")

        self.stdout.write(
            f"Selected {len(assets)} map(s) across {len(issue_dates)} issue date(s)."
        )
        if options["inventory_only"]:
            for asset in assets:
                self.stdout.write(
                    f"{asset['date']} {asset['key']} {asset['source_url']}"
                )
            return
        if options["dry_run"]:
            self._report_dry_run(assets, options["refresh"])
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
                self.stdout.write(f"SKIP {asset['date']} {asset['key']}")
                continue
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_FAILED
                and not options["retry_failures"]
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(f"SKIP {asset['date']} {asset['key']} failed")
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
                self.stderr.write(f"FAILED {asset['date']} {asset['key']}: {exc}")
                if not options["continue_on_error"]:
                    raise
        self.stdout.write(
            "Season-onset import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if failures:
            raise CommandError(f"{len(failures)} season-onset map(s) failed")

    def _report_dry_run(self, assets, refresh):
        for asset in assets:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).exists()
            action = "REFRESH" if existing and refresh else (
                "SKIP" if existing else "CREATE"
            )
            self.stdout.write(f"{action} {asset['date']} {asset['key']}")

    @staticmethod
    def _request(url, **kwargs):
        try:
            response = requests.get(
                operational_url(url),
                timeout=(10, 60),
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
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Rainfall and Seasonal Onset Monitoring",
            defaults={
                "variable_name": "rainfall-and-seasonal-onset-monitoring",
                "temporal_resolution": "pentadal",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="rainfall-and-seasonal-onset-monitoring"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Rainfall and Seasonal Onset Monitoring",
                slug="rainfall-and-seasonal-onset-monitoring",
                service=service,
                product=product,
                introduction_title="Rainfall and Seasonal Onset Monitoring",
                introduction_text=(
                    "Observed and forecast rainy-season onset monitoring maps "
                    "for Africa produced by the ACMAD Regional Climate Center."
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
            name="Season Onset Maps",
            defaults={"icon": "cloud-rain", "category_format": "jpeg"},
        )
        item_types = {}
        for key, name in PRODUCT_TYPES.items():
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=name,
                defaults={
                    "file_name_convention": f"season_onset_{key}_{{yyyy}}{{mm}}{{dd}}",
                    "valid_for_days": 5,
                },
            )
            item_types[key] = item_type
        return product_page, item_types

    @staticmethod
    def _download(asset):
        temp = tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            response = Command._request(asset["source_url"], stream=True)
            with temp:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > MAX_IMAGE_SIZE:
                        raise CommandError(
                            f"Image exceeds 20 MiB: {asset['source_url']}"
                        )
                    digest.update(chunk)
                    temp.write(chunk)
            with PillowImage.open(temp.name) as image:
                image.verify()
                if image.format != "JPEG":
                    raise CommandError(
                        f"Source did not return a JPEG: {asset['source_url']}"
                    )
            return temp.name, digest.hexdigest()
        except Exception:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            raise

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        page_slug = f"rainfall-seasonal-onset-{asset['date'].isoformat()}"
        page_title = (
            "Rainfall and Seasonal Onset Monitoring — "
            f"{asset['date'].strftime('%d %B %Y')}"
        )
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
                        image.title = f"{asset['name']} — {asset['date']}"
                        image.file.save(filename, File(handle), save=True)
                    else:
                        image = image_model(
                            title=f"{asset['name']} — {asset['date']}"
                        )
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
            self.stdout.write(f"{outcome.upper()} {asset['date']} {asset['key']}")
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
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": None,
                "image": existing.image if existing else None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
