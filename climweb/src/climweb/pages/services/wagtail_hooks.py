from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .arc2_admin import rcc_arc2_imports_view, rcc_cpc_imports_view, rcc_imports_view


@hooks.register("register_admin_urls")
def rcc_import_urls():
    return [
        path("rcc-data-imports/", rcc_imports_view, name="rcc_imports"),
        path("rcc-data-imports/arc2/", rcc_arc2_imports_view, name="rcc_arc2_imports"),
        path("rcc-data-imports/cpc-unified/", rcc_cpc_imports_view, name="rcc_cpc_imports"),
    ]


@hooks.register("register_admin_menu_item")
def rcc_import_menu():
    return MenuItem("RCC Data Imports", reverse("rcc_imports"), icon_name="download", order=292)
