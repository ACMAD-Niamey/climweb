from django.conf import settings
from django.db.models import Count, Max, Q

from climweb.pages.products.import_registry import PRODUCT_IMPORTS
from climweb.pages.products.models import ProductPage, ProductSourceImport


def build_import_monitor_rows():
    rows = []
    for definition in PRODUCT_IMPORTS:
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
        enabled = getattr(settings, definition["enabled_setting"], False)
        interval_hours = getattr(settings, definition["interval_setting"], None)
        latest_failure = (
            imports.filter(status=ProductSourceImport.STATUS_FAILED)
            .order_by("-updated_at")
            .first()
        )
        product_pages = list(
            ProductPage.objects.filter(
                product__name__in=definition["product_names"]
            )
            .live()
            .order_by("title")
        )

        if not enabled:
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
                "health": health,
                "health_label": health_label,
                "latest_failure": latest_failure,
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
