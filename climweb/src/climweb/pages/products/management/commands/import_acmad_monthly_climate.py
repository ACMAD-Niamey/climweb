import hashlib
import json
import os
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from calendar import monthrange
from datetime import date
from urllib.parse import quote, urljoin, urlparse, urlunparse

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
    "ClimateBulletin_TN/Monthly_Bulletin/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD RCC Monthly Climate Review THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Monthly-Climate-Importer/1.0 (+https://new.acmad.org/)"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
MAX_IMAGE_SIZE = 10 * 1024 * 1024

PRODUCT_SPECS = {
    "Africa_rev_rfe_total_precip.png": "Monthly Rainfall Total",
    "Africa_rev_rfe_precip_anomaly.png": "Monthly Rainfall Anomaly",
    "Africa_rev_rfe_percent_normal_precip.png": "Monthly Rainfall Percent of Normal",
    "Africa_rev_rfe_normal_precip.png": "Monthly Rainfall Climatology",
    "Africa_rev_rfe_rain_day.png": "Monthly Rainy Days",
    "Africa_rev_rfe_rain_day_anom.png": "Monthly Rainy Days Anomaly",
    "Africa_rev_rfe_HVrain_day.png": "Heavy Rain Days",
    "Africa_rev_rfe_VHvrain_day.png": "Very Heavy Rain Days",
    "Africa_rev_rfe_rain_maxCDobs.png": "Maximum Consecutive Dry Days",
    "Africa_rev_rfe_rain_maxCHVRobs.png": "Maximum Consecutive Heavy Rain Days",
    "Africa_rev_rfe_rain_maxCVHVRobs.png": "Maximum Consecutive Very Heavy Rain Days",
    "Africa_rev_rfe_rain_maxCWobs.png": "Maximum Consecutive Wet Days",
}
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


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


def parse_catalog(xml_content, catalog_url):
    """Return child catalogue references and file datasets."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid THREDDS catalogue {catalog_url}: {exc}") from exc

    references = []
    datasets = []
    href_key = f"{{{XLINK_NAMESPACE}}}href"
    title_key = f"{{{XLINK_NAMESPACE}}}title"
    for reference in root.findall(f".//{{{THREDDS_NAMESPACE}}}catalogRef"):
        href = reference.get(href_key)
        if href:
            references.append({
                "title": reference.get(title_key, ""),
                "catalog_url": canonical_url(urljoin(catalog_url, href)),
            })
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        source_path = dataset.get("urlPath")
        if source_path:
            datasets.append({
                "filename": dataset.get("name", ""),
                "source_path": source_path,
            })
    return references, datasets


def issue_date_from_catalog_url(catalog_url):
    parts = urlparse(catalog_url).path.split("/")
    for index, part in enumerate(parts):
        if len(part) == 4 and part.isdigit() and part.startswith("20"):
            if index + 1 < len(parts):
                month = MONTHS.get(parts[index + 1][:3].lower())
                if month:
                    return date(int(part), month, 1)
    return None


def asset_from_dataset(dataset, catalog_url):
    name = PRODUCT_SPECS.get(dataset["filename"])
    issue_date = issue_date_from_catalog_url(catalog_url)
    if not name or not issue_date:
        return None
    parsed = urlparse(catalog_url)
    source_url = urlunparse(parsed._replace(
        path="/thredds/fileServer/" + quote(dataset["source_path"], safe="/"),
        query="",
        fragment="",
    ))
    return {
        "key": os.path.splitext(dataset["filename"])[0].lower(),
        "name": name,
        "date": issue_date,
        "valid_until": date(
            issue_date.year,
            issue_date.month,
            monthrange(issue_date.year, issue_date.month)[1],
        ),
        "source_url": canonical_url(source_url),
        "provenance_url": canonical_url(source_url),
    }


class Command(BaseCommand):
    help = "Import current or historical ACMAD RCC monthly climate review maps."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--history-only", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--limit", type=int, default=2)
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if options["from_date"] and options["to_date"]:
            if options["from_date"] > options["to_date"]:
                raise CommandError("--from-date cannot be later than --to-date")

        assets = self._discover_assets(
            options["catalog_url"],
            include_history=options["include_history"] or options["history_only"],
        )
        grouped = {}
        for asset in assets:
            grouped.setdefault(asset["date"], []).append(asset)
        issue_dates = sorted(grouped, reverse=not options["oldest_first"])
        if options["from_date"]:
            issue_dates = [
                value for value in issue_dates if value >= options["from_date"]
            ]
        if options["to_date"]:
            issue_dates = [
                value for value in issue_dates if value <= options["to_date"]
            ]
        issue_dates = issue_dates[:options["limit"]]
        selected = [asset for value in issue_dates for asset in grouped[value]]
        self.stdout.write(
            f"Selected {len(selected)} map(s) across {len(issue_dates)} issue date(s)"
        )

        if options["inventory_only"] or options["dry_run"]:
            self._report_dry_run(selected, options["refresh"])
            return

        product_page, item_types = self._get_or_create_destination()
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        for asset in selected:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).first()
            if existing and existing.status == ProductSourceImport.STATUS_IMPORTED:
                if not options["refresh"]:
                    counts["skipped"] += 1
                    self.stdout.write(f"SKIP {asset['date']} {asset['name']}")
                    continue
            try:
                outcome = self._import_asset(
                    product_page, item_types[asset["key"]], asset, existing
                )
                counts[outcome] += 1
            except Exception as exc:
                counts["failed"] += 1
                self._record_failure(product_page, asset, existing, str(exc))
                self.stderr.write(f"FAILED {asset['date']} {asset['name']}: {exc}")
                if not options["continue_on_error"]:
                    raise
        self.stdout.write(
            "Import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )

    def _report_dry_run(self, assets, refresh):
        for asset in assets:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).exists()
            action = "REFRESH" if existing and refresh else (
                "SKIP" if existing else "CREATE"
            )
            self.stdout.write(f"{action} {asset['date']} {asset['name']}")

    def _request(self, url):
        try:
            response = requests.get(
                operational_url(url),
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _discover_assets(self, catalog_url, include_history=False):
        root_url = canonical_url(catalog_url)
        references, _ = parse_catalog(self._request(root_url).content, root_url)
        year_refs = [ref for ref in references if ref["title"].isdigit()]
        year_refs.sort(key=lambda ref: ref["title"], reverse=True)
        if not include_history:
            year_refs = year_refs[:2]

        assets = []
        for year_ref in year_refs:
            month_refs, _ = parse_catalog(
                self._request(year_ref["catalog_url"]).content,
                year_ref["catalog_url"],
            )
            for month_ref in month_refs:
                rain_url = urljoin(month_ref["catalog_url"], "Rain_Review/catalog.xml")
                try:
                    rain_refs, _ = parse_catalog(
                        self._request(rain_url).content, rain_url
                    )
                except CommandError:
                    continue
                spatial_ref = next(
                    (ref for ref in rain_refs if ref["title"] == "spatial_maps"),
                    None,
                )
                if not spatial_ref:
                    continue
                spatial_refs, _ = parse_catalog(
                    self._request(spatial_ref["catalog_url"]).content,
                    spatial_ref["catalog_url"],
                )
                africa_ref = next(
                    (ref for ref in spatial_refs if ref["title"] == "Africa"),
                    None,
                )
                if not africa_ref:
                    continue
                _, datasets = parse_catalog(
                    self._request(africa_ref["catalog_url"]).content,
                    africa_ref["catalog_url"],
                )
                for dataset in datasets:
                    asset = asset_from_dataset(dataset, africa_ref["catalog_url"])
                    if asset:
                        assets.append(asset)
        return assets

    @staticmethod
    def _get_or_create_destination():
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Monthly Climate Diagnostic Bulletin",
            defaults={
                "variable_name": "monthly-climate-diagnostic-bulletin",
                "temporal_resolution": "monthly",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="monthly-climate-diagnostic-bulletin"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Monthly Climate Diagnostic Bulletin",
                slug="monthly-climate-diagnostic-bulletin",
                service=service,
                product=product,
                introduction_title="Monthly Climate Diagnostic Bulletin",
                introduction_text=(
                    "Monthly rainfall diagnostics and climate monitoring maps "
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
            name="Monthly Rainfall Review",
            defaults={"icon": "heavy-rain", "category_format": "png"},
        )
        item_types = {}
        for filename, name in PRODUCT_SPECS.items():
            key = os.path.splitext(filename)[0].lower()
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=name,
                defaults={
                    "file_name_convention": f"{key}_{{yyyy}}_{{mm}}",
                    "valid_for_days": 31,
                },
            )
            item_types[key] = item_type
        return product_page, item_types

    def _download(self, asset):
        response = self._request(asset["source_url"])
        if len(response.content) > MAX_IMAGE_SIZE:
            raise CommandError(f"Image exceeds the 10 MiB limit: {asset['source_url']}")
        temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
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
        page_slug = f"monthly-climate-diagnostic-bulletin-{asset['date'].isoformat()}"
        display_date = asset["date"].strftime("%B %Y")
        page_title = f"Monthly Climate Diagnostic Bulletin — {display_date}"
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
                filename = f"{asset['key']}_{asset['date'].strftime('%Y%m')}.png"
                with open(temp_path, "rb") as handle:
                    if image:
                        image.title = f"{asset['name']} — {display_date}"
                        image.file.save(filename, File(handle), save=True)
                    else:
                        image = image_model(
                            title=f"{asset['name']} — {display_date}"
                        )
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
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": None,
                "image": existing.image if existing else None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
