from django.urls import path

from . import views


urlpatterns = [
    path("rcc/climsoft-resources/", views.rcc_climsoft_resources, name="rcc_climsoft_resources"),
    path("rcc/climate-indices/", views.rcc_climate_index_gallery, name="rcc_climate_index_gallery"),
    path("rcc/climate-indices/<int:asset_id>/image/", views.rcc_climate_index_file, name="rcc_climate_index_file"),
    path("rcc/ein15-model-output/", views.rcc_ein15_archive, name="rcc_ein15_archive"),
    path("rcc/ein15-model-output/<int:asset_id>/download/", views.rcc_ein15_file, name="rcc_ein15_file"),
    path("rcc/seasonal-rainfall-maps/", views.rcc_seasonal_map_gallery, name="rcc_seasonal_map_gallery"),
    path("rcc/seasonal-rainfall-maps/<int:asset_id>/image/", views.rcc_seasonal_map_file, name="rcc_seasonal_map_file"),
    path("rcc/data/cpc-unified/", views.rcc_dataset_category, {"product": "cpc-unified"}, name="rcc_cpc_dataset_category"),
    path(
        "rcc/data/cpc-unified/<slug:country>/",
        views.rcc_dataset_country,
        {"product": "cpc-unified"},
        name="rcc_cpc_dataset_country",
    ),
    path("rcc/data/arc2/", views.rcc_dataset_category, name="rcc_dataset_category"),
    path(
        "rcc/data/arc2/<slug:country>/",
        views.rcc_dataset_country,
        name="rcc_dataset_country",
    ),
    path("rcc/data/<slug:key>/", views.rcc_dataset_detail, name="rcc_dataset_detail"),
    path(
        "rcc/data/<slug:key>/download/",
        views.rcc_dataset_download,
        name="rcc_dataset_download",
    ),
]
