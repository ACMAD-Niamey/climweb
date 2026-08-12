import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, datetime, timedelta
from urllib.parse import quote, urlparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image as PillowImage
from wagtail.images import get_image_model

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
from climweb.pages.products.tasks import (
    _append_document_block,
    _append_image_block,
    _get_products_raw,
    _save_products_raw,
)


API_URL = "https://acmad.org/index.php/wp-json/wp/v2/media"
DEFAULT_SEARCH_TERMS = (
    "presac",
    "presass",
    "presagg",
    "sarcof",
    "ghacof",
    "swiocof",
    "seasonal",
)
THREDDS_ROOT = (
    "https://sgbd.acmad.org/thredds/catalog/ACMAD/PROJECTS/CLIMSA/CDD/"
    "ACTIVITIES/SERVICES/Climate_outlook_forum/RCOF_WEB"
)
THREDDS_CATALOGS = (
    "PRESASS/fcst_map",
    "PRESASS/Statement",
    "PRESAGG/statement",
    "PRESAGG/fcst_map",
    "PRESAGG/archive",
    "PRESAC/statement",
    "PRESAC/fcst_map",
    "MEDCOF/statement",
    "MEDCOF/fcst_map",
)
SOURCE_WORDPRESS = "ACMAD WordPress Media"
SOURCE_THREDDS = "ACMAD THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Seasonal-Forecast-Importer/1.0 (+https://new.acmad.org/)"
MAX_FILE_SIZE = 50 * 1024 * 1024

DOCUMENT_TERMS = re.compile(
    r"bulletin|statement|communiqu|recommendation|technical[_ -]?note|"
    r"summary|seasonal[_ -]?onset|seasonal[_ -]?climate[_ -]?forecast",
    re.I,
)
IMAGE_TERMS = re.compile(
    r"fcst|forecast|(?:^|[_ -])map(?:[_ .-]|$)|outlook|"
    r"seasonal[_ -]?onset|policy[_ -]?br(?:ie|ei)f",
    re.I,
)
EXCLUDED_TERMS = re.compile(
    r"banner|bannar|flyer|agenda|concept|programme|program_|photo|group|"
    r"training|methodolog|verification|monitoring|presentation|leadslides|"
    r"appel|annonce|tdr|terms.of.reference|press",
    re.I,
)
REGIONS = ("PRESASS", "PRESAGG", "PRESAC", "SARCOF", "GHACOF", "SWIOCOF", "MEDCOF")
SEASONS = (
    "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA",
    "JAS", "ASO", "SON", "OND", "NDJ", "DJF",
)
PRODUCT_DEFINITIONS = {
    "Seasonal Forecast Maps": {
        "slug": "seasonal-forecast-maps",
        "format": "jpg",
        "introduction": (
            "Seasonal rainfall and climate outlook maps from African regional "
            "climate outlook forums."
        ),
    },
    "Seasonal Outlook Bulletins": {
        "slug": "seasonal-outlook-bulletins",
        "format": "pdf",
        "introduction": (
            "Seasonal and long-range outlook bulletins for Africa and its regions."
        ),
    },
    "Consensus Statements and Communiqués": {
        "slug": "seasonal-consensus-statements-and-communiques",
        "format": "pdf",
        "introduction": (
            "Regional climate outlook forum consensus statements and official "
            "communiqués."
        ),
    },
    "Recommendations and Summaries": {
        "slug": "seasonal-recommendations-and-summaries",
        "format": "pdf",
        "introduction": (
            "Recommendations, summaries, and decision guidance accompanying "
            "seasonal outlooks."
        ),
    },
    "Technical Notes": {
        "slug": "seasonal-technical-notes",
        "format": "pdf",
        "introduction": (
            "Technical notes documenting seasonal forecast interpretation and "
            "supporting analysis."
        ),
    },
}


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def operational_url(source_url):
    return source_url.replace(
        "https://sgbd.acmad.org/thredds/",
        "http://sgbd.acmad.org:8080/thredds/",
    )


def infer_region(filename):
    upper = filename.upper()
    for region in REGIONS:
        if region in upper:
            return region
    return "ACMAD"


def infer_language(filename):
    upper = filename.upper()
    if re.search(r"(?:FR|VF|FRENCH)(?:[_. -]|$)", upper):
        return "French"
    if re.search(r"(?:EN|ENG|ENGLISH)(?:[_. -]|$)", upper):
        return "English"
    return ""


def infer_season(filename):
    upper = filename.upper()
    for season in SEASONS:
        if re.search(rf"(?:^|[^A-Z]){season}(?:[^A-Z]|$)", upper):
            return season
    return ""


def classify_asset(filename, mime_type, context=""):
    stem = os.path.splitext(filename)[0]
    if EXCLUDED_TERMS.search(stem):
        return None
    if mime_type == "application/pdf" and DOCUMENT_TERMS.search(stem):
        if re.search(r"recommendation|summary|policy", stem, re.I):
            family = "recommendation"
            label = "Recommendations and Summaries"
        elif re.search(r"technical[_ -]?note", stem, re.I):
            family = "technical-note"
            label = "Technical Notes"
        elif re.search(r"statement|communiqu", stem, re.I):
            family = "consensus-statement"
            label = "Consensus Statements and Communiqués"
        else:
            family = "outlook-bulletin"
            label = "Seasonal Outlook Bulletins"
        kind = "document"
    elif mime_type in {"image/jpeg", "image/jpg", "image/png"} and (
        IMAGE_TERMS.search(stem)
    ):
        family = "forecast-map"
        label = "Seasonal Forecast Maps"
        kind = "image"
    else:
        return None

    region = infer_region(context or stem)
    language = infer_language(stem)
    season = infer_season(stem)
    qualifiers = [value for value in (season, language) if value]
    name = f"{region} {label.rstrip('s')}"
    if qualifiers:
        name += f" ({', '.join(qualifiers)})"
    key_parts = [region.lower(), family, season.lower(), language.lower()]
    return {
        "key": "-".join(part for part in key_parts if part),
        "name": name,
        "category": label,
        "kind": kind,
    }


def parse_media_inventory(payload):
    if not isinstance(payload, list):
        raise CommandError("ACMAD media API did not return a JSON list")
    assets = []
    for media in payload:
        source_url = media.get("source_url", "")
        filename = os.path.basename(urlparse(source_url).path)
        definition = classify_asset(filename, media.get("mime_type", ""))
        if not definition:
            continue
        try:
            issue_date = datetime.fromisoformat(media["date"]).date()
        except (KeyError, TypeError, ValueError):
            continue
        canonical_url = source_url.replace(
            "http://acmad.org/", "https://acmad.org/"
        )
        assets.append(
            {
                **definition,
                "date": issue_date,
                "filename": filename,
                "source_url": canonical_url,
                "provenance_url": canonical_url,
                "source_system": SOURCE_WORDPRESS,
            }
        )
    return assets


def parse_thredds_catalog(xml_content):
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError("ACMAD THREDDS returned invalid XML") from exc
    assets = []
    for dataset in root.iter():
        source_path = dataset.get("urlPath")
        filename = dataset.get("name", "")
        if not source_path or not filename:
            continue
        suffix = os.path.splitext(filename)[1].lower()
        mime_type = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }.get(suffix, "")
        definition = classify_asset(filename, mime_type, source_path)
        if not definition:
            continue
        modified = next(
            (
                child.text
                for child in dataset
                if child.tag.rsplit("}", 1)[-1] == "date"
                and child.get("type") == "modified"
            ),
            None,
        )
        try:
            issue_date = datetime.fromisoformat(
                modified.replace("Z", "+00:00")
            ).date()
        except (AttributeError, ValueError):
            continue
        encoded_path = "/".join(quote(part) for part in source_path.split("/"))
        source_url = (
            "https://sgbd.acmad.org/thredds/fileServer/" + encoded_path
        )
        assets.append(
            {
                **definition,
                "date": issue_date,
                "filename": filename,
                "source_url": source_url,
                "provenance_url": source_url,
                "source_system": SOURCE_THREDDS,
            }
        )
    return assets


class Command(BaseCommand):
    help = "Import current or historical ACMAD Seasonal and Long-Range Forecasts."

    def add_arguments(self, parser):
        parser.add_argument("--api-url", action="append")
        parser.add_argument("--catalog-url", action="append")
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--history-only", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--limit", type=int, default=5)
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

        assets = self._collect_assets(options)
        assets = [
            asset
            for asset in assets
            if self._date_matches(asset["date"], options)
        ]
        assets_by_identity = {}
        for asset in assets:
            identity = (asset["date"], asset["key"])
            current = assets_by_identity.get(identity)
            if not current or self._preferred(asset, current):
                assets_by_identity[identity] = asset
        assets = list(assets_by_identity.values())

        issue_dates = sorted(
            {asset["date"] for asset in assets},
            reverse=not options["oldest_first"],
        )
        if options["history_only"]:
            issue_dates = issue_dates[1:]
        elif not options["include_history"]:
            issue_dates = issue_dates[:1]
        issue_dates = issue_dates[: options["limit"]]
        assets = [asset for asset in assets if asset["date"] in issue_dates]
        assets.sort(key=lambda asset: (asset["date"], asset["key"]))
        if not assets:
            raise CommandError("No Seasonal and Long-Range Forecast files matched")

        self.stdout.write(
            f"Selected {len(assets)} file(s) across "
            f"{len(issue_dates)} issue date(s)."
        )
        for asset in assets:
            self.stdout.write(
                f"{asset['date']} {asset['kind']} {asset['key']} "
                f"{asset['source_url']}"
            )
        if options["inventory_only"]:
            return
        if options["dry_run"]:
            self._report_dry_run(assets, options["refresh"])
            return

        destinations = self._get_or_create_destinations(assets)
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        failures = []
        for asset in assets:
            product_page, item_type = destinations[asset["key"]]
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).first()
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_IMPORTED
                and existing.product_id == product_page.product_id
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                continue
            try:
                action = self._import_asset(
                    product_page, item_type, asset, existing
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
                "Seasonal and Long-Range Forecast migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(f"{len(failures)} seasonal forecast file(s) failed")

    def _collect_assets(self, options):
        assets = []
        api_urls = options["api_url"] or [
            f"{API_URL}?search={term}&per_page=100"
            for term in DEFAULT_SEARCH_TERMS
        ]
        for url in api_urls:
            try:
                assets.extend(parse_media_inventory(self._get(url).json()))
            except requests.JSONDecodeError as exc:
                raise CommandError("ACMAD media API returned invalid JSON") from exc
        catalog_urls = options["catalog_url"] or [
            f"{THREDDS_ROOT}/{path}/catalog.xml" for path in THREDDS_CATALOGS
        ]
        for url in catalog_urls:
            assets.extend(
                parse_thredds_catalog(self._get(operational_url(url)).content)
            )
        by_url = {asset["provenance_url"]: asset for asset in assets}
        return list(by_url.values())

    @staticmethod
    def _preferred(candidate, current):
        candidate_final = "final" in candidate["filename"].lower()
        current_final = "final" in current["filename"].lower()
        if candidate_final != current_final:
            return candidate_final
        return candidate["source_url"] < current["source_url"]

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
                url,
                timeout=(10, 90),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _report_dry_run(self, assets, refresh):
        for asset in assets:
            existing = ProductSourceImport.objects.filter(
                source_url=asset["provenance_url"]
            ).first()
            action = "REFRESH" if existing and refresh else (
                "SKIP" if existing else "CREATE"
            )
            self.stdout.write(f"{action} {asset['date']} {asset['key']}")

    @staticmethod
    def _get_or_create_destinations(assets):
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")

        product_pages = {}
        product_categories = {}
        destinations = {}
        for product_name, definition in PRODUCT_DEFINITIONS.items():
            product, _ = Product.objects.get_or_create(
                name=product_name,
                defaults={
                    "variable_name": definition["slug"],
                    "temporal_resolution": "seasonal",
                },
            )
            product_page = ProductPage.objects.filter(
                slug=definition["slug"]
            ).first()
            if not product_page:
                product_page = ProductPage(
                    title=product_name,
                    slug=definition["slug"],
                    service=service,
                    product=product,
                    introduction_title=product_name,
                    introduction_text=definition["introduction"],
                    products_per_page=12,
                )
                index.add_child(instance=product_page)
                product_page.save_revision().publish()
            elif product_page.service_id != service.pk:
                product_page.service = service
                product_page.save_revision().publish()
            product_pages[product_name] = product_page
            category, _ = ProductCategory.objects.get_or_create(
                product=product_page.product,
                name=product_name,
                defaults={
                    "icon": "cloud-sun-rain",
                    "category_format": definition["format"],
                },
            )
            product_categories[product_name] = category

        for asset in assets:
            if asset["key"] in destinations:
                continue
            product_page = product_pages[asset["category"]]
            category = product_categories[asset["category"]]
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=asset["name"],
                defaults={
                    "file_name_convention": (
                        "Seasonal_Forecast_"
                        f"{asset['key'].replace('-', '_')}_{{yyyy}}{{mm}}{{dd}}"
                    ),
                    "valid_for_days": 120,
                },
            )
            destinations[asset["key"]] = (product_page, item_type)
        return destinations

    @staticmethod
    def _download(asset):
        suffix = os.path.splitext(asset["filename"])[1].lower()
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            response = Command._get(operational_url(asset["source_url"]), stream=True)
            with temp:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise CommandError("File exceeds the 50 MiB limit")
                    digest.update(chunk)
                    temp.write(chunk)
            if asset["kind"] == "document":
                with open(temp.name, "rb") as handle:
                    if handle.read(5) != b"%PDF-":
                        raise CommandError("Source did not return a PDF")
            else:
                with PillowImage.open(temp.name) as image:
                    image.verify()
                    if image.format not in {"JPEG", "PNG"}:
                        raise CommandError("Source did not return a JPEG or PNG")
            return temp.name, digest.hexdigest()
        except Exception as exc:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Invalid file {asset['source_url']}: {exc}") from exc

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        issue_date = asset["date"]
        page_slug = f"{product_page.slug}-{issue_date.isoformat()}"
        page_title = f"{product_page.title} — {issue_date.isoformat()}"
        media_title = f"{asset['name']} — {issue_date.isoformat()}"
        extension = os.path.splitext(asset["filename"])[1].lower()
        filename = (
            f"Seasonal_Forecast_{asset['key'].replace('-', '_')}_"
            f"{issue_date.strftime('%Y%m%d')}{extension}"
        )
        valid_until = issue_date + timedelta(days=119)
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
                        valid_until=valid_until,
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)
                document = None
                image = None
                with open(temp_path, "rb") as handle:
                    if asset["kind"] == "document":
                        document = (
                            existing.document
                            if existing and existing.document
                            else CustomDocumentModel(title=media_title)
                        )
                        document.title = media_title
                        document.file.save(filename, File(handle), save=True)
                        self._upsert_document(
                            page, item_type, asset, document, valid_until
                        )
                    else:
                        Image = get_image_model()
                        image = (
                            existing.image
                            if existing and existing.image
                            else Image(title=media_title)
                        )
                        image.title = media_title
                        image.file.save(filename, File(handle), save=True)
                        self._upsert_image(page, item_type, asset, image, valid_until)
                page.refresh_from_db()
                page.title = page_title
                page.date = issue_date
                page.valid_until = valid_until
                page.save_revision().publish()
                ProductSourceImport.objects.update_or_create(
                    source_url=asset["provenance_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": asset["source_system"],
                        "source_published_date": issue_date,
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": existing.attempt_count + 1 if existing else 1,
                        "document": document,
                        "image": image,
                        "product_item_page": page,
                    },
                )
            return "refreshed" if existing else "created"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _upsert_document(page, item_type, asset, document, valid_until):
        raw = _get_products_raw(page)
        for block in raw:
            value = block.get("value", {})
            if (
                block.get("type") == "document_product"
                and str(value.get("product_type")) == str(item_type.pk)
                and value.get("date") == asset["date"].isoformat()
            ):
                value["document"] = document.pk
                _save_products_raw(page, raw)
                return
        _append_document_block(page, item_type.pk, asset["date"], document, valid_until)

    @staticmethod
    def _upsert_image(page, item_type, asset, image, valid_until):
        raw = _get_products_raw(page)
        for block in raw:
            value = block.get("value", {})
            if (
                block.get("type") == "image_product"
                and str(value.get("product_type")) == str(item_type.pk)
                and value.get("date") == asset["date"].isoformat()
            ):
                value["image"] = image.pk
                _save_products_raw(page, raw)
                return
        _append_image_block(page, item_type.pk, asset["date"], image.pk, valid_until)

    @staticmethod
    def _record_failure(product_page, asset, existing, message):
        ProductSourceImport.objects.update_or_create(
            source_url=asset["provenance_url"],
            defaults={
                "product": product_page.product,
                "source_system": asset["source_system"],
                "source_published_date": asset["date"],
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": existing.document if existing else None,
                "image": existing.image if existing else None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
