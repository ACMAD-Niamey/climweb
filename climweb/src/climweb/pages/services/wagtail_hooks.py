from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .arc2_admin import (
    rcc_arc2_import_log_view, rcc_arc2_imports_view,
    rcc_cpc_import_log_view, rcc_cpc_imports_view, rcc_imports_view,
)
from .seasonal_map_admin import rcc_seasonal_map_imports_view, rcc_seasonal_map_preview
from .ein15_admin import rcc_ein15_imports_view, rcc_ein15_download
from .climate_index_admin import rcc_climate_index_imports_view


@hooks.register("register_admin_urls")
def rcc_import_urls():
    return [
        path("rcc-data-imports/", rcc_imports_view, name="rcc_imports"),
        path("rcc-data-imports/arc2/", rcc_arc2_imports_view, name="rcc_arc2_imports"),
        path("rcc-data-imports/arc2/runs/<int:run_id>/", rcc_arc2_import_log_view, name="rcc_arc2_import_log"),
        path("rcc-data-imports/cpc-unified/", rcc_cpc_imports_view, name="rcc_cpc_imports"),
        path("rcc-data-imports/cpc-unified/runs/<int:run_id>/", rcc_cpc_import_log_view, name="rcc_cpc_import_log"),
        path("rcc-data-imports/seasonal-maps/", rcc_seasonal_map_imports_view, name="rcc_seasonal_map_imports"),
        path("rcc-data-imports/seasonal-maps/preview/<int:asset_id>/", rcc_seasonal_map_preview, name="rcc_seasonal_map_preview"),
        path("rcc-data-imports/ein15/", rcc_ein15_imports_view, name="rcc_ein15_imports"),
        path("rcc-data-imports/ein15/download/<int:asset_id>/", rcc_ein15_download, name="rcc_ein15_download"),
        path("rcc-data-imports/climate-indices/", rcc_climate_index_imports_view, name="rcc_climate_index_imports"),
    ]


@hooks.register("register_admin_menu_item")
def rcc_import_menu():
    return MenuItem("RCC Data Imports", reverse("rcc_imports"), icon_name="download", order=292)
