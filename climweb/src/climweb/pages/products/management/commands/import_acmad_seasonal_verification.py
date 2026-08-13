from datetime import date
from urllib.parse import urljoin

from django.core.management.base import CommandError

from climweb.base.models import Product, ProductCategory, ProductItemType
from climweb.pages.products.management.commands.import_acmad_seasonal_forecasts import (
    Command as MixedMediaImportCommand,
    iso_date,
)
from climweb.pages.products.models import ProductIndexPage, ProductPage
from climweb.pages.products.rcc import get_rcc_service_category


DEFAULT_SOURCE_URL = "https://rcc.acmad.org/cartelongerange/cartelongrange.php"
SOURCE_SYSTEM = "ACMAD RCC Seasonal Forecast Verification"
SEASONS = (
    "December–January–February",
    "January–February–March",
    "February–March–April",
    "March–April–May",
    "April–May–June",
    "May–June–July",
    "June–July–August",
    "July–August–September",
    "August–September–October",
    "September–October–November",
    "October–November–December",
    "November–December–January",
)
ROOT_YEAR = 2016
RECOVERABLE_ARCHIVE_MAPS = {
    2014: {
        "hg": (1, 3, 4, 5, 6, 7, 9, 10, 11),
        "md": (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12),
    }
}


def build_asset(source_url, year, kind, season_number, archived=False):
    base_url = urljoin(source_url, "./")
    if archived:
        base_url = urljoin(base_url, f"{year}/")
    filename = f"hs_{kind}{season_number}.jpg"
    season = SEASONS[season_number - 1]
    is_temperature = kind == "hg"
    product_type = (
        "Temperature Verification" if is_temperature else "Precipitation Verification"
    )
    return {
        "key": f"{kind}-{season_number}",
        "name": f"{product_type} — {season}",
        "category": product_type,
        "kind": "image",
        "date": date(year, season_number, 1),
        "filename": filename,
        "source_url": urljoin(base_url, filename),
        "provenance_url": urljoin(base_url, filename),
        "source_system": SOURCE_SYSTEM,
    }


def candidate_assets(source_url=DEFAULT_SOURCE_URL):
    assets = []
    for year, archived in ((ROOT_YEAR, False), (2014, True)):
        for kind in ("hg", "md"):
            season_numbers = (
                range(1, 13)
                if not archived
                else RECOVERABLE_ARCHIVE_MAPS[year][kind]
            )
            for season_number in season_numbers:
                assets.append(
                    build_asset(source_url, year, kind, season_number, archived)
                )
    pdf_url = urljoin(source_url, "hs_md13.pdf")
    assets.append(
        {
            "key": "evaluation-report",
            "name": "Seasonal Precipitation Forecast Evaluation Report",
            "category": "Evaluation Reports",
            "kind": "document",
            "date": date(ROOT_YEAR, 12, 1),
            "filename": "hs_md13.pdf",
            "source_url": pdf_url,
            "provenance_url": pdf_url,
            "source_system": SOURCE_SYSTEM,
        }
    )
    return assets


class Command(MixedMediaImportCommand):
    help = "Import ACMAD RCC seasonal forecast verification maps and reports."
    no_files_message = "No Seasonal Forecast Verification files matched"
    completion_message = "Seasonal Forecast Verification migration complete: "
    failure_label = "seasonal verification file(s)"

    def add_arguments(self, parser):
        parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
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

    def _collect_assets(self, options):
        source_url = options["source_url"]
        self._get(source_url)
        return candidate_assets(source_url)

    @staticmethod
    def _get_or_create_destinations(assets):
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Seasonal Forecast Verification",
            defaults={
                "variable_name": "seasonal-forecast-verification",
                "temporal_resolution": "seasonal",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="seasonal-forecast-verification"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Seasonal Forecast Verification",
                slug="seasonal-forecast-verification",
                service=service,
                product=product,
                introduction_title="Seasonal Forecast Verification",
                introduction_text=(
                    "RCC maps and reports evaluating seasonal precipitation and "
                    "temperature forecasts across Africa."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        elif product_page.service_id != service.pk:
            product_page.service = service
            product_page.save_revision().publish()

        destinations = {}
        for asset in assets:
            if asset["key"] in destinations:
                continue
            category, _ = ProductCategory.objects.get_or_create(
                product=product,
                name=asset["category"],
                defaults={
                    "icon": "chart-line",
                    "category_format": (
                        "pdf" if asset["kind"] == "document" else "jpg"
                    ),
                },
            )
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=asset["name"],
                defaults={
                    "file_name_convention": (
                        "Seasonal_Verification_"
                        f"{asset['key'].replace('-', '_')}_{{yyyy}}{{mm}}{{dd}}"
                    ),
                    "valid_for_days": 3650,
                },
            )
            destinations[asset["key"]] = (product_page, item_type)
        return destinations
