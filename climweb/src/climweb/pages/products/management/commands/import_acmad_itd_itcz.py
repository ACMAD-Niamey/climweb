import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timedelta
from urllib.parse import quote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
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


DEFAULT_CATALOG_URL = (
    "https://sgbd.acmad.org/thredds/catalog/FIT/ITD_MEAN_POSITION/catalog.xml"
)
DEFAULT_CSAG_ARCHIVE_URL = (
    "https://web.csag.uct.ac.za/~lawal/Newfiles/ACMAD/S2S_Forecasts/"
)
FILE_SERVER_ROOT = "https://sgbd.acmad.org/thredds/fileServer/"
SOURCE_SYSTEM = "ACMAD SGBD THREDDS / CSAG archive"
USER_AGENT = "ACMAD-ClimWeb-ITD-ITCZ-Importer/1.0 (+https://new.acmad.org/)"
THREDDS_NAMESPACE = (
    "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
)
MAX_FILE_SIZE = 20 * 1024 * 1024

DATED_PDF = re.compile(r"^itd_mean_position_(20\d{6})\.pdf$", re.I)
DATED_MAP = re.compile(r"^ITD_(20\d{6})_\d{2}\.(png|gif|jpe?g)$", re.I)
LEGACY_MAP = re.compile(r"^FIT(20\d{6})\.(png|gif|jpe?g)$", re.I)
CSAG_DATE = re.compile(r"^(20\d{6})/$")
CSAG_SPECS = (
    (
        "daily-itd-location",
        "Daily Location of ITD at Surface (1000 hPa)",
        "Africa_DailyITDLocations_{date}.gif",
    ),
    (
        "meridional-winds-925",
        "Weekly and Daily Meridional Winds (925 hPa)",
        "Africa_925hPaVWinds_{date}.gif",
    ),
)


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


def versioned_source_url(source_url, source_version):
    parsed = urlparse(source_url)
    return urlunparse(
        parsed._replace(query=urlencode({"acmad_version": source_version}))
    )


def operational_url(source_url):
    """Use ACMAD's HTTP THREDDS port when its legacy TLS is rejected by Python."""
    parsed = urlparse(source_url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def parse_thredds_catalog(xml_content):
    """Extract audited ITD PDFs and image maps from the flat ACMAD catalogue."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise CommandError(f"Invalid ITD THREDDS catalogue: {exc}") from exc

    assets = []
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath")
        if not source_path:
            continue
        modified_node = dataset.find(f"{{{THREDDS_NAMESPACE}}}date")
        modified = (
            modified_node.text.strip()
            if modified_node is not None and modified_node.text
            else ""
        )
        match = DATED_PDF.fullmatch(filename)
        if match:
            issue_date = compact_date(match.group(1))
            kind = "document"
            key = "mean-itd-position"
            name = "Daily and Weekly Mean ITD Position"
        elif filename == "itd_mean_position.pdf" and modified:
            issue_date = date.fromisoformat(modified[:10])
            kind = "document"
            key = "mean-itd-position"
            name = "Daily and Weekly Mean ITD Position"
        else:
            match = DATED_MAP.fullmatch(filename) or LEGACY_MAP.fullmatch(filename)
            if not match:
                continue
            issue_date = compact_date(match.group(1))
            kind = "image"
            key = "itd-position-map"
            name = "ITD Position Map"

        source_url = FILE_SERVER_ROOT + quote(source_path.lstrip("/"), safe="/")
        provenance_url = (
            versioned_source_url(source_url, modified or issue_date.isoformat())
            if filename == "itd_mean_position.pdf"
            else source_url
        )
        assets.append(
            {
                "key": key,
                "name": name,
                "kind": kind,
                "date": issue_date,
                "valid_until": issue_date + timedelta(days=6),
                "filename": filename,
                "source_url": source_url,
                "provenance_url": provenance_url,
                "is_current": filename == "itd_mean_position.pdf",
            }
        )
    return assets


def parse_csag_dates(html):
    soup = BeautifulSoup(html, "html.parser")
    dates = set()
    for anchor in soup.find_all("a", href=True):
        match = CSAG_DATE.fullmatch(anchor["href"])
        if not match:
            continue
        try:
            dates.add(compact_date(match.group(1)))
        except ValueError:
            continue
    return dates


class Command(BaseCommand):
    help = "Import current or historical ACMAD ITD and ITCZ PDF/image products."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument("--csag-archive-url", default=DEFAULT_CSAG_ARCHIVE_URL)
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

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if options["from_date"] and options["to_date"] and (
            options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        catalog_assets = parse_thredds_catalog(
            self._get(options["catalog_url"]).content
        )
        if options["history_only"]:
            assets = [asset for asset in catalog_assets if not asset["is_current"]]
        elif options["include_history"]:
            assets = catalog_assets
        else:
            assets = [asset for asset in catalog_assets if asset["is_current"]]

        if options["include_history"] or options["history_only"]:
            assets.extend(self._discover_csag_assets(options["csag_archive_url"]))

        assets = [
            asset
            for asset in assets
            if self._date_matches(asset["date"], options)
        ]
        assets_by_identity = {}
        for asset in assets:
            identity = (asset["date"], asset["key"])
            existing = assets_by_identity.get(identity)
            if not existing or asset["source_url"] < existing["source_url"]:
                assets_by_identity[identity] = asset
        assets = list(assets_by_identity.values())
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
            raise CommandError("No ITD and ITCZ assets matched the selected options")

        self.stdout.write(
            f"Selected {len(assets)} asset(s) across {len(issue_dates)} issue date(s)."
        )
        for asset in assets:
            self.stdout.write(
                f"{asset['date']} {asset['kind']} {asset['key']} {asset['source_url']}"
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
                "ITD and ITCZ migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(f"{len(failures)} ITD/ITCZ asset(s) failed")

    def _discover_csag_assets(self, archive_url):
        issue_dates = parse_csag_dates(self._get(archive_url).text)
        assets = []
        for issue_date in issue_dates:
            compact = issue_date.strftime("%Y%m%d")
            base_url = urljoin(archive_url, f"{compact}/ECMWF_Files/")
            for key, name, template in CSAG_SPECS:
                filename = template.format(date=compact)
                source_url = urljoin(base_url, filename)
                assets.append(
                    {
                        "key": key,
                        "name": name,
                        "kind": "image",
                        "date": issue_date,
                        "valid_until": issue_date + timedelta(days=6),
                        "filename": filename,
                        "source_url": source_url,
                        "provenance_url": source_url,
                        "is_current": False,
                    }
                )
        return assets

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

    def _get_or_create_destination(self, assets):
        product, _ = Product.objects.get_or_create(
            name="ITD and ITCZ Monitoring",
            defaults={
                "variable_name": "itd-and-itcz-monitoring",
                "temporal_resolution": "daily",
            },
        )
        categories = {}
        item_types = {}
        for asset in assets:
            category_name = (
                "Position Bulletins"
                if asset["kind"] == "document"
                else "Position and Circulation Maps"
            )
            category_format = (
                "pdf"
                if asset["kind"] == "document"
                else os.path.splitext(asset["filename"])[1]
                .lstrip(".")
                .lower()
            )
            category_key = (category_name, category_format)
            category = categories.get(category_key)
            if not category:
                stored_name = (
                    category_name
                    if category_format in {"pdf", "png"}
                    else f"{category_name} ({category_format.upper()})"
                )
                category, _ = ProductCategory.objects.get_or_create(
                    product=product,
                    name=stored_name,
                    defaults={"icon": "map", "category_format": category_format},
                )
                categories[category_key] = category
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=asset["name"],
                defaults={
                    "file_name_convention": (
                        f"ITD_{asset['key'].replace('-', '_')}_"
                        "{yyyy}{mm}{dd}"
                    ),
                    "valid_for_days": 7,
                },
            )
            item_types[asset["key"]] = item_type

        product_page = ProductPage.objects.filter(
            slug="itd-and-itcz-monitoring"
        ).first()
        if not product_page:
            index = ProductIndexPage.objects.live().first()
            if not index:
                raise CommandError("A live ProductIndexPage was not found")
            service = ServiceCategory.objects.filter(
                name="Weather Watch and Prediction"
            ).first()
            if not service:
                raise CommandError(
                    "Service category 'Weather Watch and Prediction' was not found"
                )
            product_page = ProductPage(
                title="ITD and ITCZ Monitoring",
                slug="itd-and-itcz-monitoring",
                service=service,
                product=product,
                introduction_title="ITD and ITCZ Monitoring",
                introduction_text=(
                    "Daily and weekly monitoring of the Inter-Tropical Discontinuity "
                    "and related low-level circulation over Africa."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        return product_page, item_types

    @staticmethod
    def _download(asset):
        suffix = os.path.splitext(urlparse(asset["source_url"]).path)[1] or ".bin"
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
                            "File exceeds the 20 MiB limit: "
                            f"{asset['source_url']}"
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
                    if image.format not in {"PNG", "GIF", "JPEG"}:
                        raise CommandError(
                            f"Unsupported image format: {asset['source_url']}"
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
        page_slug = f"itd-and-itcz-monitoring-{issue_date.isoformat()}"
        page_title = f"ITD and ITCZ Monitoring — {issue_date.isoformat()}"
        media_title = f"{asset['name']} — {issue_date.isoformat()}"
        extension = os.path.splitext(asset["filename"])[1].lower()
        filename = (
            f"ITD_{asset['key'].replace('-', '_')}_"
            f"{issue_date.strftime('%Y%m%d')}{extension}"
        )
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                current_import = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                if current_import and not existing:
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
                        valid_until=asset["valid_until"],
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
                        self._upsert_document_block(page, item_type, asset, document)
                    else:
                        Image = get_image_model()
                        image = (
                            existing.image
                            if existing and existing.image
                            else Image(title=media_title)
                        )
                        image.title = media_title
                        image.file.save(filename, File(handle), save=True)
                        self._upsert_image_block(page, item_type, asset, image)
                page.refresh_from_db()
                page.title = page_title
                page.date = issue_date
                page.valid_until = asset["valid_until"]
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
    def _upsert_document_block(page, item_type, asset, document):
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
            page,
            item_type.pk,
            asset["date"],
            document,
            asset["valid_until"],
        )

    @staticmethod
    def _upsert_image_block(page, item_type, asset, image):
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
            page,
            item_type.pk,
            asset["date"],
            image.pk,
            asset["valid_until"],
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
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
