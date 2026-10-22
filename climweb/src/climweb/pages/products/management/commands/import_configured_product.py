import hashlib
import json
import os
import tempfile
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from wagtail.images import get_image_model

from climweb.base.models import CustomDocumentModel
from climweb.pages.products.import_sources import (
    get_product_import_source_values,
    inspect_product_import_source,
)
from climweb.pages.products.models import (
    ConfiguredProductImporter,
    ProductImportRun,
    ProductItemPage,
    ProductSourceImport,
)
from climweb.pages.products.tasks import (
    _append_document_block,
    _append_image_block,
)


USER_AGENT = "ACMAD-ClimWeb-Configured-Importer/1.0"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class Command(BaseCommand):
    help = "Import files using a dashboard-created product importer definition."

    def add_arguments(self, parser):
        parser.add_argument("family_key")
        parser.add_argument("--from-date")
        parser.add_argument("--to-date")
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")
        parser.add_argument("--retry-failures", action="store_true")

    def handle(self, *args, **options):
        try:
            importer = ConfiguredProductImporter.objects.select_related(
                "product_page__product", "product_item_type__category"
            ).get(key=options["family_key"])
        except ConfiguredProductImporter.DoesNotExist as exc:
            raise CommandError("Configured importer was not found") from exc
        if importer.status == ConfiguredProductImporter.STATUS_ARCHIVED:
            raise CommandError("Configured importer is archived")

        values = get_product_import_source_values(importer.key)
        preview = inspect_product_import_source(
            importer.key,
            values,
            include_history=options["include_history"],
            preview_limit=None,
        )
        assets = preview["issues"]
        from_date = options.get("from_date")
        to_date = options.get("to_date")
        if from_date:
            assets = [asset for asset in assets if asset["date"].isoformat() >= str(from_date)]
        if to_date:
            assets = [asset for asset in assets if asset["date"].isoformat() <= str(to_date)]
        assets.sort(key=lambda asset: asset["date"], reverse=not options["oldest_first"])
        assets = assets[: options["limit"]]

        self.stdout.write(f"Selected {len(assets)} file(s).")
        for asset in assets:
            self.stdout.write(f"FETCH {asset['date']} {asset['source_url']}")
            existing = ProductSourceImport.objects.filter(
                source_url=asset["source_url"]
            ).first()
            retry_failed = (
                existing
                and existing.status == ProductSourceImport.STATUS_FAILED
                and options["retry_failures"]
            )
            if existing and not options["refresh"] and not retry_failed:
                self.stdout.write(f"SKIP {asset['date']} already imported {asset['source_url']}")
                continue
            action = "REFRESH" if existing else "CREATE"
            if options["dry_run"]:
                self.stdout.write(f"{action} {asset['date']} {asset['source_url']}")
                continue
            try:
                self._import_asset(importer, values, asset, existing)
            except Exception as exc:
                self._record_failure(importer, values, asset, existing, exc)
                if not options["continue_on_error"]:
                    raise CommandError(str(exc)) from exc
                self.stderr.write(f"FAILED {asset['source_url']}: {exc}")
            else:
                self.stdout.write(f"{action}D {asset['date']} {asset['source_url']}")

    @staticmethod
    def _download(asset, headers):
        response = requests.get(
            asset["source_url"],
            timeout=(10, 120),
            headers={"User-Agent": USER_AGENT, **headers},
            stream=True,
        )
        response.raise_for_status()
        suffix = os.path.splitext(urlparse(asset["source_url"]).path)[1].lower()
        digest = hashlib.sha256()
        size = 0
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > 50 * 1024 * 1024:
                    raise CommandError("Source file exceeds the 50 MiB limit")
                digest.update(chunk)
                temp.write(chunk)
            temp.close()
            return temp.name, digest.hexdigest(), suffix
        except Exception:
            temp.close()
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            raise

    def _import_asset(self, importer, values, asset, existing):
        temp_path, checksum, suffix = self._download(
            asset, values.get("request_headers", {})
        )
        try:
            with transaction.atomic():
                product_page = importer.product_page
                item_type = importer.product_item_type
                valid_until = (
                    asset["date"] + timedelta(days=item_type.valid_for_days)
                    if item_type.valid_for_days
                    else None
                )
                slug = f"{slugify(importer.label)}-{asset['date'].isoformat()}"
                page = ProductItemPage.objects.child_of(product_page).filter(slug=slug).first()
                if page is None:
                    page = ProductItemPage(
                        title=f"{importer.label} — {asset['date'].isoformat()}",
                        slug=slug,
                        date=asset["date"],
                        valid_until=valid_until,
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)

                filename = os.path.basename(urlparse(asset["source_url"]).path)
                if suffix in IMAGE_EXTENSIONS:
                    media = existing.image if existing and existing.image else None
                    with open(temp_path, "rb") as handle:
                        if media:
                            media.title = page.title
                            media.file.save(filename, File(handle), save=True)
                        else:
                            Image = get_image_model()
                            media = Image(title=page.title)
                            media.file.save(filename, File(handle), save=True)
                    _append_image_block(
                        page, item_type.pk, asset["date"], media.pk, valid_until
                    )
                    document = None
                    image = media
                else:
                    media = existing.document if existing and existing.document else None
                    with open(temp_path, "rb") as handle:
                        if media:
                            media.title = page.title
                            media.file.save(filename, File(handle), save=True)
                        else:
                            media = CustomDocumentModel(title=page.title)
                            media.file.save(filename, File(handle), save=True)
                    _append_document_block(
                        page, item_type.pk, asset["date"], media, valid_until
                    )
                    document = media
                    image = None

                page.refresh_from_db()
                page.save_revision().publish()
                ProductSourceImport.objects.update_or_create(
                    source_url=asset["source_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": values["source_system"],
                        "source_published_date": asset["date"],
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": existing.attempt_count + 1 if existing else 1,
                        "document": document,
                        "image": image,
                        "product_item_page": page,
                    },
                )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _record_failure(importer, values, asset, existing, exc):
        ProductSourceImport.objects.update_or_create(
            source_url=asset["source_url"],
            defaults={
                "product": importer.product_page.product,
                "source_system": values["source_system"],
                "source_published_date": asset["date"],
                "checksum_sha256": "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": str(exc)[:4000],
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": existing.document if existing else None,
                "image": existing.image if existing else None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
