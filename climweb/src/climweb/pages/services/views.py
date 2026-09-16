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


def _arc2_assets():
    return RCCDatasetAsset.objects.filter(
        key__startswith="arc2-",
        synced_at__isnull=False,
    ).exclude(object_name="")


def rcc_dataset_category(request):
    countries = list(
        _arc2_assets().values("country").annotate(
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
            "data_services_page": RCCDataServicesPage.objects.live().first(),
        },
    )


def rcc_dataset_country(request, country):
    country_name = next(
        (name for name in _arc2_assets().values_list("country", flat=True).distinct() if slugify(name) == country),
        None,
    )
    if not country_name:
        raise Http404("This ARC2 country is not available.")
    return render(
        request,
        "services/rcc_dataset_country.html",
        {
            "country": country_name,
            "stations": _arc2_assets().filter(country=country_name).order_by("station"),
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
            "country_url": reverse("rcc_dataset_country", args=[slugify(asset.country)]),
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
