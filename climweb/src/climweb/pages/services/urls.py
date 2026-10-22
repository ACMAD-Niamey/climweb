from django.urls import path

from . import views


urlpatterns = [
    path(
        "rcc/long-range/consensus-statements/",
        views.rcc_consensus_forums,
        name="rcc_consensus_forums",
    ),
    path(
        "rcc/long-range/consensus-statements/<slug:forum>/",
        views.rcc_consensus_forum_detail,
        name="rcc_consensus_forum_detail",
    ),
    path(
        "rcc/long-range/tailored-forecasts/",
        views.rcc_long_range_gallery,
        {"gallery": "tailored-forecasts"},
        name="rcc_tailored_forecast_gallery",
    ),
    path(
        "rcc/long-range/model-performance/",
        views.rcc_long_range_gallery,
        {"gallery": "model-performance"},
        name="rcc_model_performance_gallery",
    ),
    path(
        "rcc/long-range/forecast-verification/",
        views.rcc_long_range_gallery,
        {"gallery": "forecast-verification"},
        name="rcc_forecast_verification_gallery",
    ),
    path("rcc/climsoft-resources/", views.rcc_climsoft_resources, name="rcc_climsoft_resources"),
    path("rcc/climate-indices/", views.rcc_climate_index_gallery, name="rcc_climate_index_gallery"),
    path("rcc/climate-indices/<int:asset_id>/image/", views.rcc_climate_index_file, name="rcc_climate_index_file"),
    path(
        "rcc/reference-climatologies/",
        views.rcc_reference_climatology_countries,
        name="rcc_reference_climatology_countries",
    ),
    path(
        "rcc/reference-climatologies/<slug:country>/",
        views.rcc_reference_climatology_country,
        name="rcc_reference_climatology_country",
    ),
    path(
        "rcc/reference-climatologies/<slug:country>/<slug:station_id>/",
        views.rcc_reference_climatology_station,
        name="rcc_reference_climatology_station",
    ),
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
