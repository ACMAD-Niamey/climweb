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
from wagtail.documents import get_document_model

from .models import (
    RCCClimateIndexAsset,
    RCCClimateMonitoringPage,
    RCCConsensusForumPage,
    RCCDataServicesPage,
    RCCDatasetAsset,
    RCCEIN15Asset,
    RCCReferenceClimatology,
    RCCSeasonalMapAsset,
    RCCLongRangeForecastingPage,
)
from climweb.pages.products.models import ProductPage
from .seasonal_map_importer import SEASONS
from .climsoft_resources import CLIMSOFT_DOCUMENTS, CLIMSOFT_DOCUMENTS_BY_TITLE


MAP_VARIANTS = (
    ("rainfall", "Mean rainfall"),
    ("1mm", "Days above 1 mm"),
    ("20mm", "Days above 20 mm"),
    ("50mm", "Days above 50 mm"),
)
EIN15_FAMILIES = ("ATM", "RAD", "SAV", "SRF", "STS")
LONG_RANGE_GALLERIES = {
    "tailored-forecasts": {
        "slug": "seasonal-forecast-maps",
        "badge": "RCC tailored forecasts",
        "title": "Tailored precipitation and temperature forecasts",
        "eyebrow": "Seasonal forecast maps",
        "intro": (
            "Explore locally managed regional and sub-regional forecast maps "
            "by year and product type."
        ),
    },
    "model-performance": {
        "slug": "seasonal-model-performance",
        "badge": "RCC model assessment",
        "title": "Statistical and dynamical model performance",
        "eyebrow": "Forecast system performance",
        "intro": (
            "Compare maps and graphs assessing statistical and dynamical "
            "seasonal forecasting systems."
        ),
    },
    "forecast-verification": {
        "slug": "seasonal-forecast-verification",
        "badge": "RCC forecast verification",
        "title": "Forecast and outlook verification",
        "eyebrow": "Verification maps and graphs",
        "intro": (
            "Review precipitation and temperature verification maps, graphs "
            "and evaluation reports."
        ),
    },
}


def rcc_consensus_forums(request):
    long_range_page = RCCLongRangeForecastingPage.objects.live().first()
    forums = (
        RCCConsensusForumPage.objects.live()
        .child_of(long_range_page)
        .order_by("path")
        if long_range_page
        else RCCConsensusForumPage.objects.none()
    )
    return render(
        request,
        "services/rcc_consensus_forums.html",
        {
            "forums": forums,
            "document_count": sum(forum.document_count for forum in forums),
            "long_range_page": long_range_page,
        },
    )


def rcc_consensus_forum_detail(request, forum):
    forum_page = get_object_or_404(
        RCCConsensusForumPage.objects.live(),
        slug=forum,
    )
    return forum_page.serve(request)


def rcc_long_range_gallery(request, gallery):
    config = LONG_RANGE_GALLERIES.get(gallery)
    if not config:
        raise Http404("This long-range forecast gallery does not exist.")

    product_page = ProductPage.objects.live().filter(slug=config["slug"]).first()
    cards = []
    if product_page:
        items = sorted(
            product_page.all_products.live().specific(),
            key=lambda item: item.date,
            reverse=True,
        )
        for item in items:
            for block in item.products:
                if block.block_type not in {"image_product", "document_product"}:
                    continue
                item_type = block.value.product_item_type()
                if not item_type:
                    continue
                cards.append(
                    {
                        "kind": "image" if block.block_type == "image_product" else "document",
                        "name": item_type.name,
                        "category": item_type.category.name,
                        "date": block.value.get("date") or item.date,
                        "image": block.value.get("image"),
                        "thumbnail": block.value.get("thumbnail"),
                        "document": block.value.get("document"),
                    }
                )

    categories = sorted({card["category"] for card in cards})
    product_names = sorted({card["name"] for card in cards})
    years = sorted({card["date"].year for card in cards}, reverse=True)
    selected_category = (request.GET.get("type") or "").strip()
    selected_product = (request.GET.get("product") or "").strip()
    selected_year = (request.GET.get("year") or "").strip()
    if selected_category not in categories:
        selected_category = ""
    if selected_product not in product_names:
        selected_product = ""
    if selected_year and selected_year not in {str(year) for year in years}:
        selected_year = ""
    filtered_cards = [
        card
        for card in cards
        if (not selected_category or card["category"] == selected_category)
        and (not selected_product or card["name"] == selected_product)
        and (not selected_year or str(card["date"].year) == selected_year)
    ]
    return render(
        request,
        "services/rcc_long_range_gallery.html",
        {
            **config,
            "cards": filtered_cards,
            "total_assets": len(cards),
            "category_options": categories,
            "product_options": product_names,
            "year_options": years,
            "selected_category": selected_category,
            "selected_product": selected_product,
            "selected_year": selected_year,
            "long_range_page": RCCLongRangeForecastingPage.objects.live().first(),
        },
    )


def _station_assets(product="arc2"):
    return RCCDatasetAsset.objects.filter(
        key__startswith=f"{product}-",
        synced_at__isnull=False,
    ).exclude(object_name="")


def rcc_dataset_category(request, product="arc2"):
    assets = _station_assets(product)
    selector_countries = [
        {"country": country, "slug": slugify(country)}
        for country in assets.values_list("country", flat=True)
        .distinct()
        .order_by("country")
    ]
    station_selector = [
        {
            "country": slugify(asset.country),
            "name": asset.station,
            "url": reverse("rcc_dataset_detail", args=[asset.key]),
        }
        for asset in assets.order_by("country", "station")
    ]
    return render(
        request,
        "services/rcc_dataset_category.html",
        {
            "selector_countries": selector_countries,
            "station_selector": station_selector,
            "product_title": "ARC2 daily station rainfall" if product == "arc2" else "CPC-Unified estimated daily rainfall",
            "product_label": "ARC2" if product == "arc2" else "CPC-Unified",
            "climate_monitoring_page": RCCClimateMonitoringPage.objects.live().first(),
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
            "climate_monitoring_page": RCCClimateMonitoringPage.objects.live().first(),
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
            "category_url_name": "rcc_cpc_dataset_category" if asset.key.startswith("cpc-unified-") else "rcc_dataset_category",
            "climate_monitoring_page": RCCClimateMonitoringPage.objects.live().first(),
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


def rcc_reference_climatology_countries(request):
    all_records = RCCReferenceClimatology.objects.all()
    selector_countries = [
        {
            "country": country,
            "slug": slugify(country),
        }
        for country in all_records.values_list("country", flat=True)
        .distinct()
        .order_by("country")
    ]
    station_selector = []
    for station in (
        all_records.values("country", "station_id", "station_name")
        .distinct()
        .order_by("country", "station_name")
    ):
        country_slug = slugify(station["country"])
        station_selector.append(
            {
                "country": country_slug,
                "id": station["station_id"],
                "name": station["station_name"],
                "url": reverse(
                    "rcc_reference_climatology_station",
                    args=[country_slug, station["station_id"]],
                ),
            }
        )
    return render(
        request,
        "services/rcc_reference_climatology_countries.html",
        {
            "selector_countries": selector_countries,
            "station_selector": station_selector,
            "climate_monitoring_page": RCCClimateMonitoringPage.objects.live().first(),
        },
    )


def _reference_country_name(country_slug):
    return next(
        (
            name
            for name in RCCReferenceClimatology.objects.values_list(
                "country", flat=True
            ).distinct()
            if slugify(name) == country_slug
        ),
        None,
    )


def rcc_reference_climatology_country(request, country):
    country_name = _reference_country_name(country)
    if not country_name:
        raise Http404("This reference-climatology country is not available.")
    search_query = (request.GET.get("q") or "").strip()[:100]
    records = RCCReferenceClimatology.objects.filter(country=country_name)
    if search_query:
        records = records.filter(station_name__icontains=search_query)
    stations = list(
        records.values("station_id", "station_name")
        .annotate(
            period_count=Count("id"),
            first_period=Min("period_start"),
            last_period=Max("period_end"),
        )
        .order_by("station_name")
    )
    return render(
        request,
        "services/rcc_reference_climatology_country.html",
        {
            "country": country_name,
            "country_slug": country,
            "stations": stations,
            "search_query": search_query,
            "climate_monitoring_page": RCCClimateMonitoringPage.objects.live().first(),
        },
    )


def rcc_reference_climatology_station(request, country, station_id):
    country_name = _reference_country_name(country)
    if not country_name:
        raise Http404("This reference-climatology country is not available.")
    records = list(
        RCCReferenceClimatology.objects.filter(
            country=country_name,
            station_id=station_id,
        ).order_by("period_start", "period_end")
    )
    if not records:
        raise Http404("This station climatology is not available.")
    period_order = {
        (1981, 1990): 0,
        (1991, 2000): 1,
        (2001, 2010): 2,
        (1981, 2010): 3,
    }
    records.sort(
        key=lambda record: period_order.get(
            (record.period_start, record.period_end),
            99,
        )
    )
    parameter_options = (
        ("precipitation", "Precipitation", "mm"),
        ("rainy_days", "Rainy days", "days"),
        ("tmin", "Mean minimum temperature", "°C"),
        ("tmean", "Mean temperature", "°C"),
        ("tmax", "Mean maximum temperature", "°C"),
    )
    parameters = {
        key: {"key": key, "label": label, "unit": unit}
        for key, label, unit in parameter_options
    }
    selected_parameter = parameters.get(
        request.GET.get("parameter", "precipitation"),
        parameters["precipitation"],
    )
    requested_period = request.GET.get("period", "")
    selected_record = next(
        (
            record
            for record in records
            if f"{record.period_start}-{record.period_end}" == requested_period
        ),
        records[0],
    )
    rows_by_month = {
        row["month"]: dict(row) for row in selected_record.monthly_data
    }
    chart_rows = []
    for month in range(1, 13):
        row = rows_by_month.get(
            month,
            {
                "month": month,
                "month_name": datetime(2000, month, 1).strftime("%B"),
                "precipitation": None,
                "rainy_days": None,
                "tmax": None,
                "tmean": None,
                "tmin": None,
            },
        )
        row["chart_value"] = row.get(selected_parameter["key"])
        chart_rows.append(row)

    available_values = [
        row["chart_value"]
        for row in chart_rows
        if row["chart_value"] is not None
    ]
    minimum = min(available_values or [0])
    maximum = max(available_values or [1])
    baseline = min(0, minimum)
    value_range = maximum - baseline or 1
    for row in chart_rows:
        value = row["chart_value"]
        row["chart_height"] = (
            round(max(3, ((value - baseline) / value_range) * 100), 1)
            if value is not None
            else 0
        )
    selected_record.chart_rows = chart_rows
    return render(
        request,
        "services/rcc_reference_climatology_station.html",
        {
            "country": country_name,
            "country_slug": country,
            "station_name": records[0].station_name,
            "station_id": station_id,
            "records": records,
            "selected_record": selected_record,
            "parameter_options": parameters.values(),
            "selected_parameter": selected_parameter,
            "climate_monitoring_page": RCCClimateMonitoringPage.objects.live().first(),
        },
    )


def rcc_climsoft_resources(request):
    query = (request.GET.get("q") or "").strip()[:100]
    selected_category = (request.GET.get("category") or "").strip()[:80]
    Document = get_document_model()
    documents = list(Document.objects.filter(tags__name="Climsoft").distinct())
    order = {item["title"]: position for position, item in enumerate(CLIMSOFT_DOCUMENTS)}
    resources = []
    for document in documents:
        metadata = CLIMSOFT_DOCUMENTS_BY_TITLE.get(document.title)
        if not metadata:
            file_name = document.file.name.lower()
            metadata = next(
                (item for item in CLIMSOFT_DOCUMENTS if file_name.endswith(item["filename"].lower())),
                {},
            )
        category = metadata.get("category", "Additional resource")
        try:
            size_bytes = document.file.size
        except OSError:
            size_bytes = document.file_size or 0
        resource = {
            "document": document,
            "category": category,
            "category_slug": slugify(category),
            "description": metadata.get("description", "Additional Climsoft resource maintained by ACMAD."),
            "format": document.file_extension.upper(),
            "order": order.get(metadata.get("title"), len(order)),
            "size_bytes": size_bytes,
        }
        resources.append(resource)
    resources.sort(key=lambda item: (item["order"], item["document"].title.lower()))
    category_options = []
    for item in CLIMSOFT_DOCUMENTS:
        option = (slugify(item["category"]), item["category"])
        if option not in category_options:
            category_options.append(option)
    if any(item["category"] == "Additional resource" for item in resources):
        category_options.append(("additional-resource", "Additional resource"))
    valid_categories = {value for value, _ in category_options}
    if selected_category not in valid_categories:
        selected_category = ""
    if query:
        needle = query.casefold()
        resources = [
            item for item in resources
            if needle in item["document"].title.casefold()
            or needle in item["description"].casefold()
            or needle in item["category"].casefold()
        ]
    if selected_category:
        resources = [item for item in resources if item["category_slug"] == selected_category]
    return render(request, "services/rcc_climsoft_resources.html", {
        "resources": resources,
        "total_resources": len(documents),
        "query": query,
        "selected_category": selected_category,
        "category_options": category_options,
        "data_services_page": RCCDataServicesPage.objects.live().first(),
    })


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
