import hashlib
import json
import os
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from datetime import date, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlencode, urlparse, urlunparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
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
    "https://sgbd.acmad.org/thredds/catalog/ACMAD/PROJECTS/CLIMSA/CDD/"
    "ACTIVITIES/SERVICES/Doc_Web/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD SGBD/THREDDS Policy Briefs"
USER_AGENT = "ACMAD-ClimWeb-Policy-Briefs-Importer/1.0 (+https://new.acmad.org/)"
THREDDS_NAMESPACE = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_PDF_SIZE = 50 * 1024 * 1024
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def canonical_source_url(url):
    """Store stable HTTPS provenance while using ACMAD's HTTP service to fetch."""
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="https", netloc="sgbd.acmad.org")
    return urlunparse(parsed)


def operational_url(url):
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def versioned_source_url(source_url, source_version):
    """Identify versions of fixed-name source files without losing their source URL."""
    parsed = urlparse(canonical_source_url(source_url))
    return urlunparse(
        parsed._replace(query=urlencode({"acmad_version": source_version}))
    )


def classify_policy_asset(filename, allow_unlisted=False):
    """Return the media kind for explicitly recognised policy-brief files."""
    basename = os.path.basename(filename)
    extension = os.path.splitext(basename)[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return None

    normalised = basename.lower().replace("-", "_")
    is_policy_brief = (
        normalised.startswith("lrf_policy_brief")
        or normalised.startswith("policy_breif")
        or normalised.startswith("policy_brief")
    )
    if not (allow_unlisted or is_policy_brief):
        return None
    return "document" if extension == ".pdf" else "image"


def parse_thredds_catalog(xml, catalog_url):
    """Extract only policy-brief PDFs and images from the shared Doc_Web folder."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid THREDDS XML at {catalog_url}: {exc}") from exc

    assets = []
    file_server_root = "https://sgbd.acmad.org/thredds/fileServer/"
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        url_path = dataset.get("urlPath")
        if not url_path:
            continue
        filename = dataset.get("name") or os.path.basename(url_path)
        media_kind = classify_policy_asset(filename)
        if not media_kind:
            continue

        modified_node = dataset.find(f"{{{THREDDS_NAMESPACE}}}date")
        modified = (
            modified_node.text.strip()
            if modified_node is not None and modified_node.text
            else None
        )
        assets.append(
            {
                "filename": filename,
                "media_kind": media_kind,
                "source_url": canonical_source_url(
                    file_server_root + quote(url_path, safe="/()")
                ),
                "source_version": modified,
                "date": date.fromisoformat(modified[:10]) if modified else None,
            }
        )
    return assets


class Command(BaseCommand):
    help = "Import ACMAD Policy and Decision Brief PDF/image assets."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument(
            "--asset-url",
            action="append",
            default=[],
            help=(
                "Import an additional PDF, PNG, or JPEG URL. This option may be "
                "repeated and accepts files outside the catalogue whitelist."
            ),
        )
        parser.add_argument(
            "--issue-date",
            type=iso_date,
            help="Override the issue date for all selected assets.",
        )
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Maximum newest issue dates to process (default: 5).",
        )
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if (
            options["from_date"]
            and options["to_date"]
            and options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        assets = self._discover_assets(options)
        for asset in assets:
            if options["issue_date"]:
                asset["date"] = options["issue_date"]
            if options["issue_date"] and not asset["source_version"]:
                asset["source_version"] = (
                    f"issue-date-{options['issue_date'].isoformat()}"
                )
            elif not asset["date"] or not asset["source_version"]:
                source_date, source_version = self._source_metadata(asset["source_url"])
                asset["date"] = source_date
                asset["source_version"] = source_version
            asset["provenance_url"] = versioned_source_url(
                asset["source_url"], asset["source_version"]
            )

        if options["from_date"]:
            assets = [
                asset for asset in assets if asset["date"] >= options["from_date"]
            ]
        if options["to_date"]:
            assets = [
                asset for asset in assets if asset["date"] <= options["to_date"]
            ]

        assets_by_provenance = {
            asset["provenance_url"]: asset for asset in assets
        }
        assets = list(assets_by_provenance.values())
        assets.sort(
            key=lambda asset: (asset["date"], asset["filename"].lower()),
            reverse=not options["oldest_first"],
        )
        selected_dates = sorted(
            {asset["date"] for asset in assets},
            reverse=not options["oldest_first"],
        )[: options["limit"]]
        assets = [asset for asset in assets if asset["date"] in selected_dates]

        if not assets:
            raise CommandError("No Policy and Decision Brief assets matched the options")

        self.stdout.write(
            f"Selected {len(assets)} asset(s) across {len(selected_dates)} issue date(s)."
        )
        for asset in assets:
            self.stdout.write(
                f"{asset['date']} {asset['media_kind'].upper()} "
                f"{asset['filename']} {asset['source_url']}"
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
                self.stdout.write(f"{action} {asset['date']} {asset['filename']}")
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
                self.stdout.write(
                    f"SKIP {asset['filename']} provenance #{existing.pk}"
                )
                continue
            try:
                action = self._import_asset(
                    product_page, item_types[asset["media_kind"]], asset, existing
                )
                counts[action] += 1
            except CommandError as exc:
                counts["failed"] += 1
                failures.append((asset["filename"], str(exc)))
                self._record_failure(product_page, asset, existing, str(exc))
                self.stderr.write(self.style.ERROR(f"FAILED {asset['filename']}: {exc}"))
                if not options["continue_on_error"]:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                "Policy briefs migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(
                f"{len(failures)} asset(s) failed: "
                + ", ".join(filename for filename, _ in failures)
            )

    def _discover_assets(self, options):
        response = self._get(options["catalog_url"])
        try:
            assets = parse_thredds_catalog(response.content, options["catalog_url"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        for asset_url in options["asset_url"]:
            filename = os.path.basename(urlparse(asset_url).path)
            media_kind = classify_policy_asset(filename, allow_unlisted=True)
            if not media_kind:
                raise CommandError(
                    f"Unsupported --asset-url file type for {asset_url}; use PDF, PNG, or JPEG"
                )
            assets.append(
                {
                    "filename": filename,
                    "media_kind": media_kind,
                    "source_url": canonical_source_url(asset_url),
                    "source_version": None,
                    "date": None,
                }
            )
        return assets

    def _get(self, url, **kwargs):
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

    def _source_metadata(self, source_url):
        try:
            response = requests.head(
                operational_url(source_url),
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Could not inspect {source_url}: {exc}") from exc
        last_modified = response.headers.get("Last-Modified")
        if not last_modified:
            raise CommandError(
                f"No Last-Modified date was provided for {source_url}; use --issue-date"
            )
        try:
            modified = parsedate_to_datetime(last_modified)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                f"Invalid Last-Modified date {last_modified!r} for {source_url}"
            ) from exc
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        return modified.date(), modified.astimezone(timezone.utc).isoformat()

    def _get_or_create_destination(self):
        product_page = ProductPage.objects.filter(
            slug="brief-policy-on-significant-weather-and-climate-events"
        ).first()
        if not product_page:
            product_page = ProductPage.objects.filter(
                slug="policy-and-decision-briefs"
            ).first()

        if product_page:
            product = product_page.product
        else:
            product, _ = Product.objects.get_or_create(
                name="Policy and Decision Briefs",
                defaults={
                    "variable_name": "policy-and-decision-briefs",
                    "temporal_resolution": "monthly",
                },
            )
            index = ProductIndexPage.objects.live().first()
            if not index:
                raise CommandError("A live ProductIndexPage was not found")
            service = ServiceCategory.objects.filter(
                name__icontains="Climate and Development"
            ).first()
            if not service:
                raise CommandError(
                    "A 'Climate and Development' service category was not found"
                )
            product_page = ProductPage(
                title="Brief Policy on Significant Weather and Climate Events",
                slug="brief-policy-on-significant-weather-and-climate-events",
                service=service,
                product=product,
                introduction_title="Policy and Decision Briefs",
                introduction_text=(
                    "Decision-focused briefs on significant weather and climate "
                    "events, their potential impacts, and recommended actions."
                ),
                products_per_page=6,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Policy and Decision Briefs ProductPage #{product_page.pk}"
                )
            )

        changed_fields = []
        if not product.variable_name:
            product.variable_name = "policy-and-decision-briefs"
            changed_fields.append("variable_name")
        if not product.temporal_resolution:
            product.temporal_resolution = "monthly"
            changed_fields.append("temporal_resolution")
        if changed_fields:
            product.save(update_fields=changed_fields)

        document_category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Brief Documents",
            defaults={"icon": "doc-full-inverse", "category_format": "pdf"},
        )
        image_category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Brief Maps and Previews",
            defaults={"icon": "map", "category_format": "png"},
        )
        document_type, _ = ProductItemType.objects.get_or_create(
            category=document_category,
            name="Policy and Decision Brief",
            defaults={
                "file_name_convention": "Policy_Decision_Brief_{yyyy}{mm}{dd}",
                "valid_for_days": 31,
            },
        )
        image_type, _ = ProductItemType.objects.get_or_create(
            category=image_category,
            name="Policy Brief Map or Preview",
            defaults={
                "file_name_convention": "Policy_Brief_Preview_{yyyy}{mm}{dd}",
                "valid_for_days": 31,
            },
        )
        return product_page, {"document": document_type, "image": image_type}

    def _download_asset(self, asset):
        extension = os.path.splitext(asset["filename"])[1].lower()
        temp = tempfile.NamedTemporaryFile(suffix=extension, delete=False)
        digest = hashlib.sha256()
        size = 0
        limit = MAX_PDF_SIZE if extension == ".pdf" else MAX_IMAGE_SIZE
        try:
            try:
                response = requests.get(
                    operational_url(asset["source_url"]),
                    timeout=(10, 120),
                    headers={"User-Agent": USER_AGENT},
                    allow_redirects=True,
                    stream=True,
                )
                response.raise_for_status()
                with temp:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > limit:
                            raise CommandError(
                                f"Asset exceeds the {limit // (1024 * 1024)} MiB "
                                f"limit: {asset['source_url']}"
                            )
                        digest.update(chunk)
                        temp.write(chunk)
            except requests.RequestException as exc:
                raise CommandError(
                    f"Could not fetch {asset['source_url']}: {exc}"
                ) from exc

            if extension == ".pdf":
                with open(temp.name, "rb") as handle:
                    if handle.read(5) != b"%PDF-":
                        raise CommandError(
                            f"Source did not return a PDF: {asset['source_url']}"
                        )
                    handle.seek(max(0, size - 1024))
                    if b"%%EOF" not in handle.read():
                        raise CommandError(
                            f"PDF is incomplete: {asset['source_url']}"
                        )
            else:
                with PillowImage.open(temp.name) as image:
                    image.verify()
                    expected = "PNG" if extension == ".png" else "JPEG"
                    if image.format != expected:
                        raise CommandError(
                            f"Expected {expected}, received {image.format}: "
                            f"{asset['source_url']}"
                        )
            return temp.name, digest.hexdigest()
        except Exception as exc:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Invalid asset {asset['source_url']}: {exc}") from exc

    @staticmethod
    def _upsert_media_block(page, item_type, asset, media):
        block_type = (
            "document_product" if asset["media_kind"] == "document" else "image_product"
        )
        media_field = "document" if asset["media_kind"] == "document" else "image"
        raw = _get_products_raw(page)
        date_string = asset["date"].isoformat()
        valid_until = (asset["date"] + timedelta(days=30)).isoformat()
        for block in raw:
            value = block.get("value", {})
            if (
                block.get("type") == block_type
                and str(value.get("product_type")) == str(item_type.pk)
                and value.get("date") == date_string
            ):
                value[media_field] = media.pk
                value["valid_until"] = valid_until
                _save_products_raw(page, raw)
                return

        if asset["media_kind"] == "document":
            _append_document_block(
                page, item_type.pk, asset["date"], media, date.fromisoformat(valid_until)
            )
        else:
            _append_image_block(
                page, item_type.pk, asset["date"], media.pk, date.fromisoformat(valid_until)
            )

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download_asset(asset)
        issue_date = asset["date"]
        valid_until = issue_date + timedelta(days=30)
        page_title = f"Policy and Decision Brief — {issue_date.isoformat()}"
        page_slug = slugify(page_title)
        extension = os.path.splitext(asset["filename"])[1].lower()
        safe_extension = ".jpg" if extension == ".jpeg" else extension
        prefix = "Policy_Decision_Brief" if asset["media_kind"] == "document" else (
            "Policy_Brief_Preview"
        )
        local_filename = f"{prefix}_{issue_date.strftime('%Y%m%d')}{safe_extension}"
        media_title = f"{item_type.name} — {issue_date.isoformat()}"
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                current_import = ProductSourceImport.objects.filter(
                    source_url=asset["provenance_url"]
                ).first()
                if current_import and not existing:
                    self.stdout.write(f"SKIP {asset['filename']} imported concurrently")
                    return "skipped"

                page = ProductItemPage.objects.child_of(product_page).filter(
                    slug=page_slug
                ).first()
                if not page:
                    page = ProductItemPage(
                        title=page_title,
                        slug=page_slug,
                        date=issue_date,
                        valid_until=valid_until,
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)

                with open(temp_path, "rb") as handle:
                    if asset["media_kind"] == "document":
                        media = existing.document if existing and existing.document else None
                        if media:
                            media.title = media_title
                            media.file.save(local_filename, File(handle), save=True)
                        else:
                            media = CustomDocumentModel(title=media_title)
                            media.file.save(local_filename, File(handle), save=True)
                    else:
                        Image = get_image_model()
                        media = existing.image if existing and existing.image else None
                        if media:
                            media.title = media_title
                            media.file.save(local_filename, File(handle), save=True)
                        else:
                            media = Image(title=media_title)
                            media.file.save(local_filename, File(handle), save=True)

                self._upsert_media_block(page, item_type, asset, media)
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
                        "document": media if asset["media_kind"] == "document" else None,
                        "image": media if asset["media_kind"] == "image" else None,
                        "product_item_page": page,
                    },
                )
            action = "refreshed" if existing else "created"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action.upper()} {asset['filename']} sha256={checksum[:12]}…"
                )
            )
            return action
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
                "image": existing.image if existing else None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
