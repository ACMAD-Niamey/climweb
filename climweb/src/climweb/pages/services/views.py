import csv
import io
from collections import deque

from django.core.files.storage import storages
from django.db.models import Count, Max, Min
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.text import slugify

from .models import RCCDataServicesPage, RCCDatasetAsset


def _station_assets(product="arc2"):
    return RCCDatasetAsset.objects.filter(
        key__startswith=f"{product}-",
        synced_at__isnull=False,
    ).exclude(object_name="")


def rcc_dataset_category(request, product="arc2"):
    countries = list(
        _station_assets(product).values("country").annotate(
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
            "product_title": "ARC2 daily station rainfall" if product == "arc2" else "CPC-Unified estimated daily rainfall",
            "product_label": "ARC2" if product == "arc2" else "CPC-Unified",
            "country_url_name": "rcc_dataset_country" if product == "arc2" else "rcc_cpc_dataset_country",
            "data_services_page": RCCDataServicesPage.objects.live().first(),
        },
    )


def rcc_dataset_country(request, country, product="arc2"):
    country_name = next(
        (name for name in _station_assets(product).values_list("country", flat=True).distinct() if slugify(name) == country),
        None,
    )
    if not country_name:
        raise Http404("This dataset country is not available.")
    return render(
        request,
        "services/rcc_dataset_country.html",
        {
            "country": country_name,
            "stations": _station_assets(product).filter(country=country_name).order_by("station"),
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
