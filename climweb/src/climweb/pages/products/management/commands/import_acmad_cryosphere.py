import json
import os
from datetime import date, timedelta

from django.core.files import File
from django.core.management.base import CommandError
from django.db import transaction

from climweb.base.models import CustomDocumentModel, Product, ProductCategory, ProductItemType
from climweb.pages.products.management.commands.import_acmad_climate_change import (
    Command as DocumentImportCommand,
)
from climweb.pages.products.models import ProductIndexPage, ProductItemPage, ProductPage, ProductSourceImport
from climweb.pages.products.rcc import get_rcc_service_category
from climweb.pages.products.tasks import _append_document_block


DEFAULT_SOURCE_URL = "https://rcc.acmad.org/climatemonitoring.php"
REPORT_URL = (
    "https://rcc.acmad.org/archive_bulletin/"
    "State_of_African_Mountain_Glacier_2020_en.pdf"
)
SOURCE_SYSTEM = "ACMAD RCC Cryosphere"


class Command(DocumentImportCommand):
    help = "Import the ACMAD RCC State of African Mountain Glaciers report."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.set_defaults(source_url=DEFAULT_SOURCE_URL)

    def _discover_assets(self, source_url):
        self._request(source_url)
        report_url = REPORT_URL if source_url == DEFAULT_SOURCE_URL else source_url
        issue_date = date(2020, 12, 31)
        return [{
            "key": "mountain-glaciers",
            "name": "State of African Mountain Glaciers",
            "date": issue_date,
            "valid_until": issue_date + timedelta(days=3650),
            "source_url": report_url,
            "provenance_url": report_url,
        }]

    @staticmethod
    def _get_or_create_destination():
        service = get_rcc_service_category()
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")
        product, _ = Product.objects.get_or_create(
            name="Cryosphere and African Mountain Glaciers",
            defaults={
                "variable_name": "cryosphere-and-african-mountain-glaciers",
                "temporal_resolution": "other",
            },
        )
        product_page = ProductPage.objects.filter(
            slug="cryosphere-and-african-mountain-glaciers"
        ).first()
        if not product_page:
            product_page = ProductPage(
                title="Cryosphere and African Mountain Glaciers",
                slug="cryosphere-and-african-mountain-glaciers",
                service=service,
                product=product,
                introduction_title="Cryosphere and African Mountain Glaciers",
                introduction_text=(
                    "RCC publications on African mountain glaciers, cryosphere "
                    "change, climate impacts, and climate services."
                ),
                products_per_page=12,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
        elif product_page.service_id != service.pk:
            product_page.service = service
            product_page.save_revision().publish()
        category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Cryosphere Reports",
            defaults={"icon": "doc-full-inverse", "category_format": "pdf"},
        )
        item_type, _ = ProductItemType.objects.get_or_create(
            category=category,
            name="State of African Mountain Glaciers Report",
            defaults={
                "file_name_convention": "african_mountain_glaciers_{yyyy}",
                "valid_for_days": 3650,
            },
        )
        return product_page, {"mountain-glaciers": item_type}

    def _import_asset(self, product_page, item_type, asset, existing):
        temp_path, checksum = self._download(asset)
        page_title = f"State of African Mountain Glaciers — {asset['date'].year}"
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                page = ProductItemPage.objects.child_of(product_page).filter(
                    slug="state-of-african-mountain-glaciers-2020"
                ).first()
                if not page:
                    page = ProductItemPage(
                        title=page_title,
                        slug="state-of-african-mountain-glaciers-2020",
                        date=asset["date"],
                        valid_until=asset["valid_until"],
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)
                document = existing.document if existing and existing.document else None
                with open(temp_path, "rb") as handle:
                    if document:
                        document.title = page_title
                        document.file.save("african_mountain_glaciers_2020.pdf", File(handle), save=True)
                    else:
                        document = CustomDocumentModel(title=page_title)
                        document.file.save("african_mountain_glaciers_2020.pdf", File(handle), save=True)
                _append_document_block(page, item_type.pk, asset["date"], document, asset["valid_until"])
                page.refresh_from_db()
                page.title = page_title
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
            return "refreshed" if existing else "created"
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
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message[:4000],
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": existing.document if existing else None,
                "image": None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
