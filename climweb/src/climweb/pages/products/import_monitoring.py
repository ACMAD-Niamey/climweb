from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.db.models import Count, Max, Q

from climweb.pages.products.import_registry import get_product_import_definitions
from climweb.pages.products.models import (
    ProductImportSchedule,
    ProductPage,
    ProductSourceImport,
)


def _latest_import_file(imports):
    latest_import = (
        imports.filter(status=ProductSourceImport.STATUS_IMPORTED)
        .select_related("document", "image", "product_item_page")
        .order_by("-imported_at")
        .first()
    )
    if latest_import is None:
        return None

    filename = unquote(
        PurePosixPath(urlsplit(latest_import.source_url).path).name
    )
    file_url = latest_import.source_url

    if latest_import.document_id:
        filename = latest_import.document.filename or filename
        file_url = latest_import.document.url
    elif latest_import.image_id:
        filename = latest_import.image.filename or filename
        file_url = latest_import.image.file.url
    elif latest_import.product_item_page_id:
        file_url = latest_import.product_item_page.url or file_url

    return {
        "name": filename or latest_import.source_url,
        "url": file_url,
        "source_url": latest_import.source_url,
        "source_system": latest_import.source_system,
        "source_published_date": latest_import.source_published_date,
        "imported_at": latest_import.imported_at,
    }


def build_import_monitor_rows():
    schedule_values = ProductImportSchedule.objects.values_list(
        "product_family", "interval_hours", "enabled_override"
    )
    saved_schedules = {
        family: {
            "interval_hours": interval_hours,
            "enabled_override": enabled_override,
        }
        for family, interval_hours, enabled_override in schedule_values
    }
    rows = []
    for definition in get_product_import_definitions():
        imports = ProductSourceImport.objects.filter(
            product__name__in=definition["product_names"]
        )
        stats = imports.aggregate(
            imported_count=Count(
                "id",
                filter=Q(status=ProductSourceImport.STATUS_IMPORTED),
            ),
            failed_count=Count(
                "id",
                filter=Q(status=ProductSourceImport.STATUS_FAILED),
            ),
            latest_source_date=Max(
                "source_published_date",
                filter=Q(status=ProductSourceImport.STATUS_IMPORTED),
            ),
            last_activity=Max("updated_at"),
        )
        default_enabled = (
            definition.get("default_enabled", False)
            if definition.get("is_configured")
            else getattr(settings, definition["enabled_setting"], False)
        )
        saved_schedule = saved_schedules.get(definition["key"], {})
        enabled_override = saved_schedule.get("enabled_override")
        enabled = (
            default_enabled if enabled_override is None else enabled_override
        )
        default_interval_hours = (
            definition.get("default_interval_hours")
            if definition.get("is_configured")
            else getattr(settings, definition["interval_setting"], None)
        )
        interval_hours = saved_schedule.get(
            "interval_hours", default_interval_hours
        )
        latest_failure = (
            imports.filter(status=ProductSourceImport.STATUS_FAILED)
            .order_by("-updated_at")
            .first()
        )
        latest_import_file = _latest_import_file(imports)
        product_pages = list(
            ProductPage.objects.filter(
                product__name__in=definition["product_names"]
            )
            .live()
            .order_by("title")
        )

        if definition.get("is_archived"):
            health = "archived"
            health_label = "Archived"
        elif not enabled:
            health = "disabled"
            health_label = "Disabled"
        elif stats["failed_count"]:
            health = "attention"
            health_label = "Attention"
        elif stats["imported_count"]:
            health = "healthy"
            health_label = "Healthy"
        else:
            health = "unseeded"
            health_label = "Not seeded"

        rows.append(
            {
                **definition,
                **stats,
                "enabled": enabled,
                "interval_hours": interval_hours,
                "interval_is_custom": definition["key"] in saved_schedules,
                "enabled_is_custom": enabled_override is not None,
                "health": health,
                "health_label": health_label,
                "latest_failure": latest_failure,
                "latest_import_file": latest_import_file,
                "product_pages": product_pages,
            }
        )
    return rows


def build_import_monitor_summary(rows):
    return {
        "families": len(rows),
        "enabled": sum(1 for row in rows if row["enabled"]),
        "imported": sum(row["imported_count"] for row in rows),
        "failed": sum(row["failed_count"] for row in rows),
        "attention": sum(1 for row in rows if row["health"] == "attention"),
    }
