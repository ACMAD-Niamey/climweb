import json
import os
import re
import xml.etree.ElementTree as ElementTree
from calendar import monthrange
from datetime import date, timedelta
from urllib.parse import quote, urlparse, urlunparse

from django.core.files import File
from django.core.management.base import CommandError
from django.db import transaction

from climweb.base.models import (
    CustomDocumentModel,
    Product,
    ProductCategory,
    ProductItemType,
)
from climweb.pages.products.management.commands.import_acmad_climate_change import (
    Command as DocumentImportCommand,
    iso_date,
)
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
from climweb.pages.products.tasks import _append_document_block


DEFAULT_CATALOG_URL = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "DroughtMonitoringService/catalog.xml"
)
LEGACY_BULLETIN_URL = (
    "https://rcc.acmad.org/archive_bulletin/ACMAD_bulletin_mesa.pdf"
)
SOURCE_SYSTEM = "ACMAD RCC Drought Monitoring THREDDS"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
MONTH_PATTERN = re.compile(
    r"Bulletin_(?:No\.)?(?P<month>\d{1,2})_"
    r"(?:(?:[A-Za-z]+)_)?(?P<year>20\d{2})\.pdf$",
    re.IGNORECASE,
)
REPORT_SPECS = {
    "drought-bulletin": {
        "name": "Drought and Seasonal Climate Forecast Bulletin",
        "category": "Drought and Seasonal Climate Forecast Bulletins",
    },
    "climate-watch-bulletin": {
        "name": "ACMAD Climate Watch Bulletin",
        "category": "Archived Climate Watch Bulletins",
    },
}


def parse_catalog(xml_content, catalog_url):
    """Extract dated drought-bulletin PDFs from a THREDDS catalogue."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid THREDDS catalogue {catalog_url}: {exc}") from exc

    parsed = urlparse(catalog_url)
    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath")
        match = MONTH_PATTERN.search(filename)
        if not source_path or not match:
            continue
        month = int(match.group("month"))
        year = int(match.group("year"))
        if month not in range(1, 13):
            continue
        issue_date = date(year, month, 1)
        source_url = urlunparse(
            parsed._replace(
                path="/thredds/fileServer/" + quote(source_path, safe="/"),
                query="",
                fragment="",
            )
        )
        assets.append(
            {
                "key": "drought-bulletin",
                "date": issue_date,
                "valid_until": date(year, month, monthrange(year, month)[1]),
                "source_url": operational_url(source_url),
                "provenance_url": canonical_url(source_url),
            }
        )
    return assets


class Command(DocumentImportCommand):
    help = "Import ACMAD RCC Climate Watch and drought-monitoring PDF bulletins."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--history-only", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--limit", type=int, default=5)
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
        assets = [
            asset
            for asset in assets
            if not (options["from_date"] and asset["date"] < options["from_date"])
            and not (options["to_date"] and asset["date"] > options["to_date"])
        ]
        assets.sort(
            key=lambda asset: asset["date"],
            reverse=not options["oldest_first"],
        )
        assets = assets[: options["limit"]]
        if not assets:
            raise CommandError(
                "No Climate Watch bulletins matched the selected options"
            )

        self.stdout.write(f"Selected {len(assets)} bulletin(s).")
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
            "Climate Watch import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if failures:
            raise CommandError(f"{len(failures)} Climate Watch bulletin(s) failed")

    def _request(self, url, method="get", **kwargs):
        return super()._request(operational_url(url), method=method, **kwargs)

    def _discover_assets(self, catalog_url):
        response = self._request(canonical_url(catalog_url))
        assets = parse_catalog(response.content, canonical_url(catalog_url))
        if canonical_url(catalog_url).rstrip("/") == canonical_url(
            DEFAULT_CATALOG_URL
        ).rstrip("/"):
            assets.append(
                {
                    "key": "climate-watch-bulletin",
                    "date": date(2014, 12, 31),
                    "valid_until": date(2014, 12, 31) + timedelta(days=3650),
                    "source_url": LEGACY_BULLETIN_URL,
                    "provenance_url": LEGACY_BULLETIN_URL,
                }
            )
        return assets

    @staticmethod
    def _get_or_create_destination():
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Climate Watch Bulletin",
            defaults={
                "variable_name": "climate-watch-bulletin",
                "temporal_resolution": "monthly",
            },
        )
        product_page = ProductPage.objects.filter(slug="climate-watch-bulletin").first()
        if not product_page:
            product_page = ProductPage(
                title="Climate Watch Bulletin",
                slug="climate-watch-bulletin",
                service=service,
                product=product,
                introduction_title="Climate Watch Bulletin",
                introduction_text=(
                    "ACMAD Regional Climate Center bulletins monitoring drought, "
                    "rainfall, vegetation, environmental conditions, and "
                    "seasonal climate."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        elif product_page.service_id != service.pk:
            product_page.service = service
            product_page.save_revision().publish()

        item_types = {}
        for key, spec in REPORT_SPECS.items():
            category, _ = ProductCategory.objects.get_or_create(
                product=product,
                name=spec["category"],
                defaults={"icon": "doc-full-inverse", "category_format": "pdf"},
            )
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=spec["name"],
                defaults={
                    "file_name_convention": f"{key}_{{yyyy}}{{mm}}",
                    "valid_for_days": 31 if key == "drought-bulletin" else 3650,
                },
            )
            item_types[key] = item_type
        return product_page, item_types

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        spec = REPORT_SPECS[asset["key"]]
        date_label = asset["date"].strftime("%B %Y")
        page_slug = f"climate-watch-{asset['date'].isoformat()}-{asset['key']}"
        page_title = f"{spec['name']} — {date_label}"
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
                document = existing.document if existing and existing.document else None
                filename = f"{asset['key']}_{asset['date'].strftime('%Y%m%d')}.pdf"
                with open(temp_path, "rb") as handle:
                    if document:
                        document.title = page_title
                        document.file.save(filename, File(handle), save=True)
                    else:
                        document = CustomDocumentModel(title=page_title)
                        document.file.save(filename, File(handle), save=True)
                _append_document_block(
                    page, item_type.pk, asset["date"], document, asset["valid_until"]
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
                        "document": document,
                        "image": None,
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
                "checksum_sha256": "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message[:4000],
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": existing.document if existing else None,
                "image": None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
