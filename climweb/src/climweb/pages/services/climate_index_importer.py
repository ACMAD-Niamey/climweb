"""Safely preserve the historical RCC climate-index PNG gallery."""

import hashlib
import io

import requests
from PIL import Image, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.db import transaction
from django.utils import timezone

from .models import RCCClimateIndexAsset


SOURCE_ROOT = "https://rcc.acmad.org/graphmap"
MAX_PNG_BYTES = 10 * 1024 * 1024
INDEX_TITLES = (
    "Rainfall anomalies and trends, Central African Republic (1951–2010)",
    "Interannual variability of surface temperature in the study areas",
    "Standardized rainfall anomaly cycle (1951–2010)",
    "Observed and simulated annual rainfall cycle",
    "Mean temperature anomalies and trends",
    "Observed and simulated annual precipitation anomalies and trends",
    "Correlation of observed and simulated rainfall",
    "Observed and simulated monthly temperature cycle",
    "Observed and simulated annual temperature anomalies and trends",
    "Correlation of observed and simulated temperature",
    "Precipitation scenarios for Bouar station (1971–2000 and 2071–2100)",
    "Temperature scenarios for Bouar station (1971–2000 and 2071–2100)",
    "Crop-yield change under A1 and B1 emissions scenarios",
    "Africa temperature anomalies and trends (1950–2015)",
    "Annual cycle of African temperatures (2016)",
    "Ranked subregional temperature anomalies (1950–2014)",
    "Ranked Africa temperature anomalies (1950–2015)",
    "Africa temperature anomalies (1950–2014)",
    "Africa temperature-anomaly trends (1950–2016 and since 1990)",
    "Temperature-anomaly trends across six African subregions",
    "Ranked temperature anomalies (2014)",
    "Ranked temperature anomalies (2016)",
)


def chart_details(index):
    try:
        index = int(index)
        title = INDEX_TITLES[index - 1]
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("Climate-index chart number must be between 1 and 22.") from exc
    scope = "central-africa" if index <= 13 else "africa"
    return index, title, scope


def sync_chart(index):
    index, title, scope = chart_details(index)
    source_url = f"{SOURCE_ROOT}/hs_hg{index}.png"
    with requests.get(source_url, stream=True, timeout=(15, 90), allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("The chart source did not return a direct response.")
        data = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            data.extend(chunk)
            if len(data) > MAX_PNG_BYTES:
                raise ValueError("The chart exceeds the size limit.")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The source is not a PNG image.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG":
                raise ValueError("The source is not a PNG image.")
            width, height = image.size
            if width * height > 25_000_000:
                raise ValueError("The chart exceeds the pixel limit.")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The source PNG could not be decoded.") from exc

    checksum = hashlib.sha256(data).hexdigest()
    object_name = f"climate-indices/hs_hg{index}/{checksum[:16]}.png"
    storage = storages["rcc_data"]
    if not storage.exists(object_name):
        storage.save(object_name, ContentFile(data))
    with transaction.atomic():
        asset, _ = RCCClimateIndexAsset.objects.update_or_create(
            legacy_index=index,
            defaults={
                "title": title,
                "scope": scope,
                "source_url": source_url,
                "object_name": object_name,
                "checksum_sha256": checksum,
                "size_bytes": len(data),
                "width": width,
                "height": height,
                "synced_at": timezone.now(),
            },
        )
    return asset
