import json
import os
import re
from datetime import date, timedelta
from urllib.parse import unquote, urljoin, urlparse

from django.core.files import File
from django.core.management.base import CommandError
from django.db import transaction

from climweb.base.models import Product, ProductCategory, ProductItemType
from climweb.pages.products.management.commands.import_acmad_climate_change import (
    Command as DocumentImportCommand,
    iso_date,
)
from climweb.pages.products.models import (
    ProductIndexPage,
    ProductItemPage,
    ProductPage,
    ProductSourceImport,
)
from climweb.pages.products.rcc import get_rcc_service_category
from climweb.pages.products.tasks import _append_document_block


DEFAULT_SOURCE_URL = "https://rcc.acmad.org/annualbulletin.php"
SOURCE_SYSTEM = "ACMAD RCC Annual Climate Reports"
YEAR_PATTERN = re.compile(r"(?<!\d)(20(?:1[2-9]|2\d))(?!\d)")
YEAR_RANGE_PATTERN = re.compile(
    r"(?<!\d)(20(?:1[2-9]|2\d))[_\-](20(?:1[2-9]|2\d))(?!\d)"
)
REPORT_SPECS = {
    "wmo-report": {
        "name": "WMO State of the Climate in Africa Report",
        "category": "Annual State of Climate Reports",
    },
    "acmad-assessment": {
        "name": "ACMAD Annual Climate Assessment",
        "category": "ACMAD Annual Climate Assessments",
    },
    "multi-year-summary": {
        "name": "ACMAD Multi-year Climate Summary",
        "category": "ACMAD Annual Climate Assessments",
    },
}

# The RCC page links provisional WMO editions for some years. These audited
# THREDDS files are the corresponding final editions and take precedence.
FINAL_REPORTS = (
    (
        "wmo-report",
        2022,
        "http://sgbd.acmad.org:8080/thredds/fileServer/ACMAD/CDD/"
        "stateofclimate/WMO_STATE_OF_CLIMATE/2022/"
        "1330_State%20of%20the%20Climate%20in%20Africa%202022_en.pdf",
    ),
    (
        "wmo-report",
        2021,
        "http://sgbd.acmad.org:8080/thredds/fileServer/ACMAD/CDD/"
        "stateofclimate/WMO_STATE_OF_CLIMATE/2021/"
        "1300_WMO_State_of_the_Climate_in_Africa_2021_en.pdf",
    ),
    (
        "wmo-report",
        2020,
        "http://sgbd.acmad.org:8080/thredds/fileServer/ACMAD/CDD/"
        "stateofclimate/WMO_STATE_OF_CLIMATE/"
        "State%20of%20the%20Climate%20in%20Africa%202020.pdf",
    ),
    (
        "wmo-report",
        2019,
        "http://sgbd.acmad.org:8080/thredds/fileServer/ACMAD/CDD/"
        "stateofclimate/WMO_STATE_OF_CLIMATE/"
        "State%20of%20the%20Climate%20in%20Africa%202019_en.pdf",
    ),
)


def parse_annual_report_links(html, source_url=DEFAULT_SOURCE_URL):
    """Extract dated PDF reports from the RCC annual-bulletin archive."""
    from bs4 import BeautifulSoup

    assets = []
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        report_url = urljoin(source_url, anchor["href"])
        parsed_path = unquote(urlparse(report_url).path)
        if not parsed_path.lower().endswith(".pdf"):
            continue
        # The legacy page contains malformed, nested anchors, so anchor text can
        # include labels belonging to later links. Classify from the URL path.
        lowered = parsed_path.lower()
        if "guideline" in lowered:
            continue
        years = [int(value) for value in YEAR_PATTERN.findall(parsed_path)]
        if not years:
            continue
        year_range = YEAR_RANGE_PATTERN.search(parsed_path)
        if year_range:
            key = "multi-year-summary"
            report_year = int(year_range.group(2))
        elif "wmo_state_of_climate" in lowered or "wmo" in lowered:
            key = "wmo-report"
            report_year = max(years)
        elif "state of the climate in africa" in lowered and "acmad" not in lowered:
            key = "wmo-report"
            report_year = max(years)
        else:
            key = "acmad-assessment"
            report_year = max(years)
        priority = 10 if "provisional" in lowered or "preliminary" in lowered else 20
        assets.append(
            {
                "key": key,
                "year": report_year,
                "date": date(report_year, 12, 31),
                "valid_until": date(report_year, 12, 31) + timedelta(days=3650),
                "source_url": report_url,
                "provenance_url": report_url,
                "priority": priority,
            }
        )
    return assets


def select_preferred_reports(assets):
    """Keep the best edition for each report type and reference year."""
    selected = {}
    for asset in assets:
        identity = (asset["key"], asset["year"])
        if (
            identity not in selected
            or asset["priority"] > selected[identity]["priority"]
        ):
            selected[identity] = asset
    return list(selected.values())


class Command(DocumentImportCommand):
    help = "Import ACMAD RCC annual state-of-the-climate PDF reports."

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
            if not (options["from_date"] and asset["date"] < options["from_date"])
            and not (options["to_date"] and asset["date"] > options["to_date"])
        ]
        assets.sort(
            key=lambda asset: (asset["date"], asset["key"]),
            reverse=not options["oldest_first"],
        )
        selected_years = []
        for asset in assets:
            if asset["year"] not in selected_years:
                selected_years.append(asset["year"])
        selected_years = set(selected_years[: options["limit"]])
        assets = [asset for asset in assets if asset["year"] in selected_years]
        if not assets:
            raise CommandError("No annual climate reports matched the selected options")

        self.stdout.write(
            f"Selected {len(assets)} report(s) across {len(selected_years)} year(s)."
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
                self.stdout.write(f"SKIP {asset['year']} {asset['key']}")
                continue
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_FAILED
                and not options["retry_failures"]
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(f"SKIP {asset['year']} {asset['key']} failed")
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
                self.stderr.write(f"FAILED {asset['year']} {asset['key']}: {exc}")
                if not options["continue_on_error"]:
                    raise
        self.stdout.write(
            "Annual climate import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if failures:
            raise CommandError(f"{len(failures)} annual climate report(s) failed")

    def _discover_assets(self, source_url):
        response = self._request(source_url)
        assets = parse_annual_report_links(response.text, source_url)
        if source_url.rstrip("/") == DEFAULT_SOURCE_URL.rstrip("/"):
            for key, report_year, report_url in FINAL_REPORTS:
                assets.append(
                    {
                        "key": key,
                        "year": report_year,
                        "date": date(report_year, 12, 31),
                        "valid_until": date(report_year, 12, 31)
                        + timedelta(days=3650),
                        "source_url": report_url,
                        "provenance_url": report_url,
                        "priority": 100,
                    }
                )
        return select_preferred_reports(assets)

    @staticmethod
    def _get_or_create_destination():
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Annual State of the Climate Report",
            defaults={
                "variable_name": "annual-state-of-the-climate-report",
                "temporal_resolution": "yearly",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="annual-state-of-the-climate-report"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Annual State of the Climate Report",
                slug="annual-state-of-the-climate-report",
                service=service,
                product=product,
                introduction_title="Annual State of the Climate Report",
                introduction_text=(
                    "Annual WMO and ACMAD assessments of observed climate "
                    "conditions, extremes, impacts, and trends across Africa."
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
                    "file_name_convention": f"{key}_{{yyyy}}",
                    "valid_for_days": 3650,
                },
            )
            item_types[key] = item_type
        return product_page, item_types

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        spec = REPORT_SPECS[asset["key"]]
        page_slug = f"annual-climate-{asset['year']}-{asset['key']}"
        page_title = f"{spec['name']} — {asset['year']}"
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
                filename = f"{asset['key']}_{asset['year']}.pdf"
                with open(temp_path, "rb") as handle:
                    if document:
                        document.title = page_title
                        document.file.save(filename, File(handle), save=True)
                    else:
                        from climweb.base.models import CustomDocumentModel

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
            self.stdout.write(f"{outcome.upper()} {asset['year']} {asset['key']}")
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
