import hashlib
import json
import os
import tempfile
from argparse import ArgumentTypeError
from datetime import date, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from climweb.base.models import (
    CustomDocumentModel,
    Product,
    ProductCategory,
    ProductItemType,
)
from climweb.pages.products.models import (
    ProductIndexPage,
    ProductItemPage,
    ProductPage,
    ProductSourceImport,
)
from climweb.pages.products.rcc import get_rcc_service_category
from climweb.pages.products.tasks import _append_document_block


DEFAULT_SOURCE_URL = "https://rcc.acmad.org/recomandation.php"
SOURCE_SYSTEM = "ACMAD RCC Highly Recommended Functions"
USER_AGENT = "ACMAD-ClimWeb-Climate-Change-Importer/1.0 (+https://new.acmad.org/)"
MAX_PDF_SIZE = 20 * 1024 * 1024
REPORT_SPECS = {
    "rapport_diallo_acmad.pdf": {
        "key": "model-scenario-report",
        "name": "Model Intercomparison and Climate Scenario Report",
        "category": "Climate Projections and Scenarios",
    },
    "doukpolo_rapport_final.pdf": {
        "key": "climate-risk-study",
        "name": "Climate Variability and Risk Study",
        "category": "Climate Variability and Risk Studies",
    },
}


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def parse_report_links(html, source_url=DEFAULT_SOURCE_URL):
    """Return the two audited RCC climate-change report links."""
    soup = BeautifulSoup(html, "html.parser")
    assets = []
    for anchor in soup.find_all("a", href=True):
        report_url = urljoin(source_url, anchor["href"])
        filename = os.path.basename(urlparse(report_url).path)
        spec = REPORT_SPECS.get(filename.lower())
        if spec:
            assets.append({
                **spec,
                "filename": filename,
                "source_url": report_url,
                "provenance_url": report_url,
            })
    return {asset["source_url"]: asset for asset in assets}.values()


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


class Command(BaseCommand):
    help = "Import ACMAD RCC climate-change and climate-projection PDF reports."

    def add_arguments(self, parser):
        parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
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

        assets = self._discover_assets(options["source_url"])
        assets = [
            asset
            for asset in assets
            if not (
                options["from_date"] and asset["date"] < options["from_date"]
            )
            and not (options["to_date"] and asset["date"] > options["to_date"])
        ]
        assets.sort(
            key=lambda asset: asset["date"],
            reverse=not options["oldest_first"],
        )
        assets = assets[: options["limit"]]
        if not assets:
            raise CommandError("No climate-change reports matched the selected options")

        self.stdout.write(f"Selected {len(assets)} report(s).")
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
            "Climate-change import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if failures:
            raise CommandError(f"{len(failures)} climate-change report(s) failed")

    def _discover_assets(self, source_url):
        response = self._request(source_url)
        assets = list(parse_report_links(response.text, source_url))
        for asset in assets:
            metadata = self._request(asset["source_url"], method="head")
            asset["date"] = header_date(metadata.headers)
            if not asset["date"]:
                raise CommandError(
                    f"No Last-Modified date for {asset['source_url']}"
                )
            asset["valid_until"] = asset["date"] + timedelta(days=3650)
        return assets

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
    def _request(url, method="get", **kwargs):
        try:
            request = requests.head if method == "head" else requests.get
            response = request(
                url,
                timeout=(10, 120),
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
            name="Climate Change and Climate Projections",
            defaults={
                "variable_name": "climate-change-and-climate-projections",
                "temporal_resolution": "other",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="climate-change-and-climate-projections"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Climate Change and Climate Projections",
                slug="climate-change-and-climate-projections",
                service=service,
                product=product,
                introduction_title="Climate Change and Climate Projections",
                introduction_text=(
                    "RCC reports on climate projections, scenarios, variability, "
                    "risk, and the expected impacts of global warming over Africa."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        elif product_page.service_id != service.pk:
            product_page.service = service
            product_page.save_revision().publish()

        item_types = {}
        for spec in REPORT_SPECS.values():
            category, _ = ProductCategory.objects.get_or_create(
                product=product,
                name=spec["category"],
                defaults={"icon": "doc-full-inverse", "category_format": "pdf"},
            )
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=spec["name"],
                defaults={
                    "file_name_convention": f"{spec['key']}_{{yyyy}}{{mm}}{{dd}}",
                    "valid_for_days": 3650,
                },
            )
            item_types[spec["key"]] = item_type
        return product_page, item_types

    @staticmethod
    def _download(asset):
        temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            response = Command._request(asset["source_url"], stream=True)
            with temp:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > MAX_PDF_SIZE:
                        raise CommandError(
                            f"PDF exceeds 20 MiB: {asset['source_url']}"
                        )
                    digest.update(chunk)
                    temp.write(chunk)
            with open(temp.name, "rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise CommandError(
                        f"Source did not return a PDF: {asset['source_url']}"
                    )
                handle.seek(max(0, size - 1024))
                if b"%%EOF" not in handle.read():
                    raise CommandError(f"PDF is incomplete: {asset['source_url']}")
            return temp.name, digest.hexdigest()
        except Exception:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            raise

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        page_slug = f"climate-change-report-{asset['date'].isoformat()}-{asset['key']}"
        page_title = f"{asset['name']} — {asset['date'].strftime('%Y')}"
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
                document = (
                    existing.document if existing and existing.document else None
                )
                filename = f"{asset['key']}_{asset['date'].strftime('%Y%m%d')}.pdf"
                with open(temp_path, "rb") as handle:
                    if document:
                        document.title = page_title
                        document.file.save(filename, File(handle), save=True)
                    else:
                        document = CustomDocumentModel(title=page_title)
                        document.file.save(filename, File(handle), save=True)
                _append_document_block(
                    page,
                    item_type.pk,
                    asset["date"],
                    document,
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
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": existing.document if existing else None,
                "image": None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
