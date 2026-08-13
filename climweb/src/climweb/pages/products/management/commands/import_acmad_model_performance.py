import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.core.management.base import CommandError

from climweb.base.models import Product, ProductCategory, ProductItemType
from climweb.pages.products.management.commands.import_acmad_seasonal_forecasts import (
    Command as MixedMediaImportCommand,
    iso_date,
)
from climweb.pages.products.models import ProductIndexPage, ProductPage
from climweb.pages.products.rcc import get_rcc_service_category


DEFAULT_SOURCE_URL = "https://rcc.acmad.org/longerange.php"
SOURCE_SYSTEM = "ACMAD RCC Seasonal Model Performance"
STATIC_SELECTOR = "https://rcc.acmad.org/modelestatique/modelstatique.php"
DYNAMIC_SELECTOR = "https://rcc.acmad.org/modeledynamique/modeledynamique.php"
STATIC_ARCHIVES = {
    2012: tuple((kind, number) for kind in ("hg", "md") for number in range(1, 13)),
    2013: tuple(
        (kind, number)
        for kind in ("hg", "md")
        for number in range(1, 13)
        if (kind, number) not in {("hg", 6), ("hg", 11)}
    ),
    2014: tuple(("hg", number) for number in range(1, 20)),
    2015: tuple(("hg", number) for number in range(8, 20)),
}
DYNAMIC_FILES = tuple(
    (kind, number)
    for kind in ("hg", "md")
    for number in range(1, 27)
    if (kind, number) not in {("md", 2), ("md", 13)}
)
SEASON_MONTHS = {
    "JFM": 1,
    "FMA": 2,
    "MAM": 3,
    "AMJ": 4,
    "MJJ": 5,
    "JJA": 6,
    "JAS": 7,
    "ASO": 8,
    "SON": 9,
    "OND": 10,
    "NDJ": 11,
    "DJF": 12,
}
MONTH_NAMES = {
    "jan": 1,
    "feb": 2,
    "fev": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def parse_options(html):
    labels = []
    for option in BeautifulSoup(html, "html.parser").find_all("option"):
        direct_text = option.find(string=True, recursive=False)
        labels.append(direct_text.strip() if direct_text else "")
    return labels


def season_month(label, fallback):
    upper = label.upper()
    for code, month in SEASON_MONTHS.items():
        if re.search(rf"(?:^|[_\-]){code}(?:$|[_\-])", upper):
            return month
    first = re.split(r"[_\-]", label.strip())[0].lower()[:4]
    for token, month in MONTH_NAMES.items():
        if first.startswith(token):
            return month
    return fallback


def model_name(label, kind, legacy=False):
    lowered = label.lower()
    if legacy:
        return "Canadian Statistical Model" if kind == "hg" else "NCEP Statistical Model"
    if "nmme" in lowered or "nmm" in lowered:
        return "NMME"
    if "cfs" in lowered:
        return "CFS"
    if "ncep" in lowered or "obs" in lowered:
        return "Observed NCEP"
    if "cmc" in lowered or "can" in lowered:
        return "CMC2"
    return "Other Model"


def make_asset(selector_url, year, family, kind, number, label, legacy=False):
    month = season_month(label, ((number - 1) % 12) + 1)
    model = model_name(label, kind, legacy)
    if family == "dynamic":
        variable = "Precipitation" if kind == "hg" else "Temperature"
        category = "Dynamical Model Skill Maps"
        key = f"dynamic-{variable.lower()}-{model.lower().replace(' ', '-')}"
        name = f"{variable} — {model}"
    else:
        category = "Statistical Model Performance"
        key = f"statistical-{model.lower().replace(' ', '-')}"
        name = model
    filename = f"hs_{kind}{number}.jpg"
    return {
        "key": key,
        "name": name,
        "category": category,
        "kind": "image",
        "date": date(year, month, 1),
        "filename": filename,
        "source_url": urljoin(selector_url, filename),
        "provenance_url": urljoin(selector_url, filename),
        "source_system": SOURCE_SYSTEM,
    }


class Command(MixedMediaImportCommand):
    help = "Import ACMAD RCC statistical and dynamical model-performance maps."
    no_files_message = "No Seasonal Model Performance maps matched"
    completion_message = "Seasonal Model Performance migration complete: "
    failure_label = "model-performance map(s)"

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
        static_url = STATIC_SELECTOR
        dynamic_url = DYNAMIC_SELECTOR
        if source_url != DEFAULT_SOURCE_URL:
            static_url = source_url

        static_options = parse_options(self._get(static_url).content)
        dynamic_options = parse_options(self._get(dynamic_url).content)
        assets = []
        for number, label in enumerate(static_options, 1):
            assets.append(
                make_asset(static_url, 2017, "static", "hg", number, label)
            )
        for year, files in STATIC_ARCHIVES.items():
            archive_url = urljoin(static_url, f"{year}/modelstatique{year}.php")
            labels = parse_options(self._get(archive_url).content)
            for kind, number in files:
                label = labels[number - 1]
                assets.append(
                    make_asset(
                        archive_url,
                        year,
                        "static",
                        kind,
                        number,
                        label,
                        legacy=year in {2012, 2013},
                    )
                )
        for kind, number in DYNAMIC_FILES:
            label = dynamic_options[number - 1]
            assets.append(
                make_asset(dynamic_url, 2014, "dynamic", kind, number, label)
            )
        return assets

    @staticmethod
    def _get_or_create_destinations(assets):
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Seasonal Model Performance",
            defaults={
                "variable_name": "seasonal-model-performance",
                "temporal_resolution": "seasonal",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="seasonal-model-performance"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Seasonal Model Performance",
                slug="seasonal-model-performance",
                service=service,
                product=product,
                introduction_title="Seasonal Model Performance",
                introduction_text=(
                    "RCC statistical correlation maps and dynamical model skill "
                    "maps used to assess seasonal forecasting systems."
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
                defaults={"icon": "chart-line", "category_format": "jpg"},
            )
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=asset["name"],
                defaults={
                    "file_name_convention": (
                        "Seasonal_Model_Performance_"
                        f"{asset['key'].replace('-', '_')}_{{yyyy}}{{mm}}{{dd}}"
                    ),
                    "valid_for_days": 3650,
                },
            )
            destinations[asset["key"]] = (product_page, item_type)
        return destinations
