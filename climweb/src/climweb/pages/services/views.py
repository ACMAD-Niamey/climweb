import csv
import io
from collections import deque
from datetime import datetime

from django.core.files.storage import storages
from django.db.models import Count, Max, Min
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.text import slugify

from .models import (
    RCCClimateIndexAsset,
    RCCDataServicesPage,
    RCCDatasetAsset,
    RCCEIN15Asset,
    RCCSeasonalMapAsset,
)
from .seasonal_map_importer import SEASONS


MAP_VARIANTS = (
    ("rainfall", "Mean rainfall"),
    ("1mm", "Days above 1 mm"),
    ("20mm", "Days above 20 mm"),
    ("50mm", "Days above 50 mm"),
)
EIN15_FAMILIES = ("ATM", "RAD", "SAV", "SRF", "STS")


def _station_assets(product="arc2"):
    return RCCDatasetAsset.objects.filter(
        key__startswith=f"{product}-",
        synced_at__isnull=False,
    ).exclude(object_name="")


def rcc_dataset_category(request, product="arc2"):
    search_query = (request.GET.get("q") or "").strip()[:100]
    assets = _station_assets(product)
    if search_query:
        assets = assets.filter(country__icontains=search_query)
    countries = list(
        assets.values("country").annotate(
            station_count=Count("id"),
            coverage_start=Min("coverage_start"),
            coverage_end=Max("coverage_end"),
        ).order_by("country")
    )
    for country in countries:
        country["slug"] = slugify(country["country"])
    return render(
        request,
        "services/rcc_dataset_category.html",
        {
            "countries": countries,
            "search_query": search_query,
            "product_title": "ARC2 daily station rainfall" if product == "arc2" else "CPC-Unified estimated daily rainfall",
            "product_label": "ARC2" if product == "arc2" else "CPC-Unified",
            "country_url_name": "rcc_dataset_country" if product == "arc2" else "rcc_cpc_dataset_country",
            "data_services_page": RCCDataServicesPage.objects.live().first(),
        },
    )


def rcc_dataset_country(request, country, product="arc2"):
    search_query = (request.GET.get("q") or "").strip()[:100]
    country_name = next(
        (name for name in _station_assets(product).values_list("country", flat=True).distinct() if slugify(name) == country),
        None,
    )
    if not country_name:
        raise Http404("This dataset country is not available.")
    stations = _station_assets(product).filter(country=country_name)
    if search_query:
        stations = stations.filter(station__icontains=search_query)
    return render(
        request,
        "services/rcc_dataset_country.html",
        {
            "country": country_name,
            "stations": stations.order_by("station"),
            "search_query": search_query,
            "product_label": "ARC2" if product == "arc2" else "CPC-Unified",
            "category_url_name": "rcc_dataset_category" if product == "arc2" else "rcc_cpc_dataset_category",
            "data_services_page": RCCDataServicesPage.objects.live().first(),
        },
    )


def _available_asset(key):
    asset = get_object_or_404(RCCDatasetAsset, key=key)
    storage = storages["rcc_data"]
    if not asset.is_available or not storage.exists(asset.object_name):
        raise Http404("This RCC dataset has not been synchronized yet.")
    return asset, storage


def rcc_dataset_detail(request, key):
    asset, storage = _available_asset(key)
    preview = deque(maxlen=8)
    with storage.open(asset.object_name, "rb") as source:
        text_source = io.TextIOWrapper(source, encoding="utf-8-sig", newline="")
        preview.extend(csv.DictReader(text_source))

    return render(
        request,
        "services/rcc_dataset_detail.html",
        {
            "asset": asset,
            "preview": list(preview),
            "country_url": reverse(
                "rcc_cpc_dataset_country" if asset.key.startswith("cpc-unified-") else "rcc_dataset_country",
                args=[slugify(asset.country)],
            ),
            "product_label": "CPC-Unified" if asset.key.startswith("cpc-unified-") else "ARC2",
            "data_services_page": RCCDataServicesPage.objects.live().first(),
        },
    )


def rcc_dataset_download(request, key):
    asset, storage = _available_asset(key)
    response = FileResponse(
        storage.open(asset.object_name, "rb"),
        as_attachment=True,
        filename=asset.original_filename or f"{asset.key}.csv",
        content_type="text/csv",
    )
    response["Content-Length"] = asset.size_bytes
    response["X-Checksum-SHA256"] = asset.checksum_sha256
    return response


def rcc_seasonal_map_gallery(request):
    season = request.GET.get("season", "")
    variant = request.GET.get("type", "")
    if season not in SEASONS:
        season = ""
    if variant not in dict(MAP_VARIANTS):
        variant = ""
    maps = RCCSeasonalMapAsset.objects.all()
    total_maps = maps.count()
    if season:
        maps = maps.filter(season=season)
    if variant:
        maps = maps.filter(variant=variant)
    labels = dict(MAP_VARIANTS)
    cards = [{"asset": asset, "variant_label": labels.get(asset.variant, asset.variant)} for asset in maps]
    return render(request, "services/rcc_seasonal_map_gallery.html", {
        "cards": cards,
        "total_maps": total_maps,
        "season_options": SEASONS,
        "variant_options": MAP_VARIANTS,
        "selected_season": season,
        "selected_variant": variant,
        "data_services_page": RCCDataServicesPage.objects.live().first(),
    })


def rcc_seasonal_map_file(request, asset_id):
    asset = get_object_or_404(RCCSeasonalMapAsset, pk=asset_id)
    storage = storages["rcc_data"]
    if not storage.exists(asset.object_name):
        raise Http404("This seasonal map is not available.")
    download = request.GET.get("download") == "1"
    response = FileResponse(
        storage.open(asset.object_name, "rb"),
        as_attachment=download,
        filename=asset.filename if download else None,
        content_type="image/png",
    )
    response["Content-Length"] = asset.size_bytes
    response["X-Checksum-SHA256"] = asset.checksum_sha256
    response["X-Content-Type-Options"] = "nosniff"
    return response


def rcc_climate_index_gallery(request):
    scope = request.GET.get("scope", "")
    if scope not in {"central-africa", "africa", "other"}:
        scope = ""
    assets = RCCClimateIndexAsset.objects.filter(active=True, synced_at__isnull=False).exclude(object_name="")
    total_charts = assets.count()
    if scope:
        assets = assets.filter(scope=scope)
    return render(request, "services/rcc_climate_index_gallery.html", {
        "assets": assets,
        "total_charts": total_charts,
        "selected_scope": scope,
        "data_services_page": RCCDataServicesPage.objects.live().first(),
    })


def rcc_climate_index_file(request, asset_id):
    asset = get_object_or_404(RCCClimateIndexAsset, pk=asset_id, synced_at__isnull=False)
    storage = storages["rcc_data"]
    if not asset.object_name or not storage.exists(asset.object_name):
        raise Http404("This climate-index chart is not available.")
    download = request.GET.get("download") == "1"
    filename = f"climate-index-{asset.legacy_index:02d}.png"
    response = FileResponse(
        storage.open(asset.object_name, "rb"),
        as_attachment=download,
        filename=filename if download else None,
        content_type="image/png",
    )
    response["Content-Length"] = asset.size_bytes
    response["X-Checksum-SHA256"] = asset.checksum_sha256
    response["X-Content-Type-Options"] = "nosniff"
    return response


def rcc_ein15_archive(request):
    family = request.GET.get("type", "")
    if family not in EIN15_FAMILIES:
        family = ""
    assets = RCCEIN15Asset.objects.all()
    total_files = assets.count()
    if family:
        assets = assets.filter(filename__startswith=f"WAfr50_{family}.")
    cards = []
    for asset in assets:
        parts = asset.filename.split(".")
        stamp = parts[1] if len(parts) > 1 else ""
        try:
            timestamp = datetime.strptime(stamp, "%Y%m%d%H").strftime("%d %b %Y · %H:00")
        except ValueError:
            timestamp = stamp
        cards.append({
            "asset": asset,
            "family": asset.filename.split("_", 1)[-1].split(".", 1)[0],
            "timestamp": timestamp,
        })
    return render(request, "services/rcc_ein15_archive.html", {
        "cards": cards,
        "total_files": total_files,
        "families": EIN15_FAMILIES,
        "selected_family": family,
        "data_services_page": RCCDataServicesPage.objects.live().first(),
    })


def rcc_ein15_file(request, asset_id):
    asset = get_object_or_404(RCCEIN15Asset, pk=asset_id)
    storage = storages["rcc_data"]
    if not storage.exists(asset.object_name):
        raise Http404("This EIN15 file is not available.")
    response = FileResponse(
        storage.open(asset.object_name, "rb"),
        as_attachment=True,
        filename=asset.filename,
        content_type="application/x-netcdf",
    )
    response["Content-Length"] = asset.size_bytes
    response["X-Checksum-SHA256"] = asset.checksum_sha256
    response["X-Content-Type-Options"] = "nosniff"
    return response
