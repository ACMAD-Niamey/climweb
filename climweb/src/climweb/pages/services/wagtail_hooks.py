from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .arc2_admin import rcc_arc2_imports_view


@hooks.register("register_admin_urls")
def rcc_import_urls():
    return [path("rcc-data-imports/", rcc_arc2_imports_view, name="rcc_arc2_imports")]


@hooks.register("register_admin_menu_item")
def rcc_import_menu():
    return MenuItem("RCC Data Imports", reverse("rcc_arc2_imports"), icon_name="download", order=292)
