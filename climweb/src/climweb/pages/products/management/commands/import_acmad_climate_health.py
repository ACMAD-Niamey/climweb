import hashlib
import json
import os
import re
import tempfile
from argparse import ArgumentTypeError
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

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
    ServiceCategory,
)
from climweb.pages.products.models import (
    ProductIndexPage,
    ProductItemPage,
    ProductPage,
    ProductSourceImport,
)
from climweb.pages.products.tasks import (
    _append_document_block,
    _append_image_block,
    _get_products_raw,
    _save_products_raw,
)


DEFAULT_API_URL = (
    "https://acmad.org/index.php/wp-json/wp/v2/media"
    "?search=meningitis&per_page=100"
)
SOURCE_SYSTEM = "ACMAD WordPress Media"
USER_AGENT = "ACMAD-ClimWeb-Climate-Health-Importer/1.0 (+https://new.acmad.org/)"
MAX_FILE_SIZE = 50 * 1024 * 1024

COMPACT_DATE = re.compile(r"(?<!\d)(20\d{6})(?!\d)")
WEEKLY_BULLETIN = re.compile(
    r"(?:acmad_)?meningitis_bulletin_"
    r"(?:\d{1,3}_20\d{2}|20\d{6})(?:-\d+)?\.pdf(?:\.pdf)?$",
    re.I,
)
TECHNICAL_NOTE = re.compile(
    r"acmad_meningitis-climenv-factors_tn_(20\d{6})\.pdf$",
    re.I,
)
VERIFICATION_REPORT = re.compile(
    r"draft-meningitis-vigilance-map-verification\.pdf$",
    re.I,
)

IMAGE_SPECS = {
    "meningitis_bulletin": {
        "key": "relative-humidity-forecast",
        "name": "Relative Humidity Forecast for Meningitis Risk",
        "date": date(2024, 4, 25),
    },
    "meningitis_bulletin2": {
        "key": "meningitis-vigilance-outlook",
        "name": "Meningitis Vigilance Outlook",
        "date": date(2024, 4, 25),
    },
    "meningitis-watches-warningd-alerts-12": {
        "key": "meningitis-vigilance-outlook",
        "name": "Meningitis Vigilance Outlook",
        "date": date(2024, 1, 8),
    },
    "climate-and-health-monitoring-meningitis-and-heat-waves": {
        "key": "meningitis-outlook-verification",
        "name": "Meningitis Outlook Verification",
        "date": date(2024, 4, 8),
    },
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


def parse_media_inventory(payload):
    """Select audited bulletin PDFs, technical notes, and health-risk images."""
    if not isinstance(payload, list):
        raise CommandError("ACMAD media API did not return a JSON list")

    assets = []
    for media in payload:
        source_url = media.get("source_url", "")
        filename = os.path.basename(urlparse(source_url).path)
        slug = media.get("slug", "").lower()
        mime_type = media.get("mime_type", "")
        try:
            media_date = datetime.fromisoformat(media["date"]).date()
        except (KeyError, TypeError, ValueError):
            continue

        definition = None
        technical_match = TECHNICAL_NOTE.fullmatch(filename)
        if mime_type == "application/pdf" and technical_match:
            definition = {
                "key": "climate-health-technical-note",
                "name": "Meningitis Climate and Environmental Factors Technical Note",
                "kind": "document",
                "date": compact_date(technical_match.group(1)),
            }
        elif mime_type == "application/pdf" and VERIFICATION_REPORT.fullmatch(filename):
            definition = {
                "key": "meningitis-outlook-verification-report",
                "name": "Meningitis Outlook Verification Report",
                "kind": "document",
                # The PDF states that it verifies the outlook for 2-8 April 2024.
                "date": date(2024, 4, 8),
            }
        elif mime_type == "application/pdf" and WEEKLY_BULLETIN.fullmatch(filename):
            date_match = COMPACT_DATE.search(filename)
            definition = {
                "key": "weekly-meningitis-bulletin",
                "name": "Weekly Meningitis Bulletin",
                "kind": "document",
                "date": (
                    compact_date(date_match.group(1))
                    if date_match
                    else media_date
                ),
            }
        elif mime_type in {"image/jpeg", "image/jpg"} and slug in IMAGE_SPECS:
            definition = {
                **IMAGE_SPECS[slug],
                "kind": "image",
            }
        if not definition:
            continue

        assets.append(
            {
                **definition,
                "filename": filename,
                "source_url": source_url.replace(
                    "http://acmad.org/", "https://acmad.org/"
                ),
                "provenance_url": source_url.replace(
                    "http://acmad.org/", "https://acmad.org/"
                ),
                "media_id": media.get("id"),
            }
        )
    return assets


class Command(BaseCommand):
    help = "Import current or historical ACMAD Climate and Health files."

    def add_arguments(self, parser):
        parser.add_argument("--api-url", default=DEFAULT_API_URL)
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

        try:
            payload = self._get(options["api_url"]).json()
        except requests.JSONDecodeError as exc:
            raise CommandError("ACMAD media API returned invalid JSON") from exc
        assets = parse_media_inventory(payload)
        assets = [
            asset
            for asset in assets
            if self._date_matches(asset["date"], options)
        ]
        assets_by_identity = {}
        for asset in assets:
            identity = (asset["date"], asset["key"])
            current = assets_by_identity.get(identity)
            if not current or asset["source_url"] < current["source_url"]:
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
        assets.sort(
            key=lambda asset: (
                asset["date"]
                if options["oldest_first"]
                else -asset["date"].toordinal(),
                asset["key"],
            )
        )
        if not assets:
            raise CommandError("No Climate and Health files matched the options")

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
            for asset in assets:
                existing = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                action = "REFRESH" if existing and options["refresh"] else (
                    "SKIP" if existing else "CREATE"
                )
                self.stdout.write(f"{action} {asset['date']} {asset['key']}")
            return

        product_page, item_types = self._get_or_create_destination(assets)
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
                continue
            try:
                action = self._import_asset(
                    product_page, item_types[asset["key"]], asset, existing
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
                "Climate and Health migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(f"{len(failures)} Climate and Health file(s) failed")

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

    @staticmethod
    def _get_or_create_destination(assets):
        product, _ = Product.objects.get_or_create(
            name="Climate and Health",
            defaults={
                "variable_name": "climate-and-health",
                "temporal_resolution": "weekly",
            },
        )
        categories = {}
        item_types = {}
        definitions = {asset["key"]: asset for asset in assets}
        for key, definition in definitions.items():
            category_name = (
                "Health Risk Maps"
                if definition["kind"] == "image"
                else "Health Bulletins and Technical Notes"
            )
            category = categories.get(category_name)
            if not category:
                category, _ = ProductCategory.objects.get_or_create(
                    product=product,
                    name=category_name,
                    defaults={
                        "icon": "heart-pulse",
                        "category_format": (
                            "jpg" if definition["kind"] == "image" else "pdf"
                        ),
                    },
                )
                categories[category_name] = category
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=definition["name"],
                defaults={
                    "file_name_convention": (
                        f"Climate_Health_{key.replace('-', '_')}_"
                        "{yyyy}{mm}{dd}"
                    ),
                    "valid_for_days": 7,
                },
            )
            item_types[key] = item_type

        product_page = ProductPage.objects.filter(slug="climate-and-health").first()
        if not product_page:
            index = ProductIndexPage.objects.live().first()
            if not index:
                raise CommandError("A live ProductIndexPage was not found")
            service = ServiceCategory.objects.filter(
                name="Climate Monitoring and Assessment"
            ).first()
            if not service:
                service = ServiceCategory.objects.filter(
                    name="Weather Watch and Prediction"
                ).first()
            if not service:
                raise CommandError(
                    "A suitable Climate and Health service was not found"
                )
            product_page = ProductPage(
                title="Climate and Health",
                slug="climate-and-health",
                service=service,
                product=product,
                introduction_title="Climate and Health",
                introduction_text=(
                    "Climate-informed meningitis bulletins, vigilance outlooks, "
                    "environmental-risk forecasts, and product verification for Africa."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        return product_page, item_types

    @staticmethod
    def _download(asset):
        suffix = ".pdf" if asset["kind"] == "document" else ".jpg"
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            response = Command._get(asset["source_url"], stream=True)
            with temp:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise CommandError(
                            f"File exceeds the 50 MiB limit: {asset['source_url']}"
                        )
                    digest.update(chunk)
                    temp.write(chunk)
            if asset["kind"] == "document":
                with open(temp.name, "rb") as handle:
                    if handle.read(5) != b"%PDF-":
                        raise CommandError(
                            f"Source did not return a PDF: {asset['source_url']}"
                        )
            else:
                with PillowImage.open(temp.name) as image:
                    image.verify()
                    if image.format != "JPEG":
                        raise CommandError(
                            f"Source did not return a JPEG: {asset['source_url']}"
                        )
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
        page_slug = f"climate-and-health-{issue_date.isoformat()}"
        page_title = f"Climate and Health — {issue_date.isoformat()}"
        media_title = f"{asset['name']} — {issue_date.isoformat()}"
        extension = ".pdf" if asset["kind"] == "document" else ".jpg"
        filename = (
            f"Climate_Health_{asset['key'].replace('-', '_')}_"
            f"{issue_date.strftime('%Y%m%d')}{extension}"
        )
        valid_until = issue_date + timedelta(days=6)
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
                        self._upsert_document_block(
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
                        self._upsert_image_block(
                            page, item_type, asset, image, valid_until
                        )
                page.refresh_from_db()
                page.title = page_title
                page.date = issue_date
                page.valid_until = valid_until
                page.save_revision().publish()
                ProductSourceImport.objects.update_or_create(
                    source_url=asset["provenance_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": SOURCE_SYSTEM,
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
    def _upsert_document_block(page, item_type, asset, document, valid_until):
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
        _append_document_block(
            page, item_type.pk, asset["date"], document, valid_until
        )

    @staticmethod
    def _upsert_image_block(page, item_type, asset, image, valid_until):
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
        _append_image_block(
            page, item_type.pk, asset["date"], image.pk, valid_until
        )

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
                "image": existing.image if existing else None,
                "product_item_page": (
                    existing.product_item_page if existing else None
                ),
            },
        )
