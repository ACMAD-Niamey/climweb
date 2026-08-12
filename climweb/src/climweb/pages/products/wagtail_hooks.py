from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin import widgets as wagtail_admin_widgets
from wagtail.admin.menu import MenuItem

from .models import ProductPage
from .views import (
    product_import_family_view,
    product_import_monitor_view,
    product_import_status_view,
    product_layers_integration_view,
    trigger_product_ingestion_view,
)


@hooks.register('register_admin_urls')
def urlconf_products():
    return [
        path(
            'product-layers-integration/<int:product_page_id>',
            product_layers_integration_view,
            name="product_layer_integration",
        ),
        path(
            'product-run-ingestion/<int:product_page_id>',
            trigger_product_ingestion_view,
            name="product_run_ingestion",
        ),
        path(
            'product-imports/',
            product_import_monitor_view,
            name="product_import_monitor",
        ),
        path(
            'product-imports/status/',
            product_import_status_view,
            name="product_import_status",
        ),
        path(
            'product-imports/<slug:family_key>/status/',
            product_import_status_view,
            name="product_import_family_status",
        ),
        path(
            'product-imports/<slug:family_key>/',
            product_import_family_view,
            name="product_import_family",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_product_import_monitor_menu_item():
    return MenuItem(
        "Product Imports",
        reverse("product_import_monitor"),
        icon_name="history",
        order=290,
    )


@hooks.register('register_page_listing_buttons')
def page_listing_buttons(page, user, next_url=None):
    if isinstance(page, ProductPage):
        yield wagtail_admin_widgets.PageListingButton(
            "MapViewer Integration",
            reverse("product_layer_integration", args=[page.pk]),
            priority=50,
        )
        if page.product.ingestion_enabled:
            yield wagtail_admin_widgets.PageListingButton(
                "Run Ingestion",
                reverse("product_run_ingestion", args=[page.pk]),
                priority=60,
            )
