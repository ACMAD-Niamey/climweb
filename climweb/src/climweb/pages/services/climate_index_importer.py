"""Safely preserve the historical RCC climate-index PNG gallery."""

import hashlib
import io

import requests
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.db import transaction
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from urllib.parse import urlsplit

from .models import RCCClimateIndexAsset, RCCClimateIndexVersion


SOURCE_ROOT = "https://rcc.acmad.org/graphmap"
MAX_PNG_BYTES = 10 * 1024 * 1024
SCHEDULE_NAME = "rcc-climate-indices-import"
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


def validate_source_url(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValidationError("Invalid graph source URL.") from exc
    allowed = getattr(settings, "RCC_CLIMATE_INDEX_ALLOWED_SOURCE_HOSTS", ("rcc.acmad.org",))
    if isinstance(allowed, str):
        allowed = [host.strip() for host in allowed.split(",") if host.strip()]
    if (
        parsed.scheme != "https" or parsed.hostname not in allowed or not parsed.netloc
        or parsed.username or parsed.password or parsed.query or parsed.fragment or port == 0
        or not parsed.path.lower().endswith(".png")
    ):
        raise ValidationError("Use an approved HTTPS PNG source URL.")
    return parsed


def legacy_asset(index):
    index, title, scope = chart_details(index)
    source_url = f"{SOURCE_ROOT}/hs_hg{index}.png"
    asset, _ = RCCClimateIndexAsset.objects.get_or_create(
        legacy_index=index,
        defaults={"title": title, "scope": scope, "source_url": source_url},
    )
    return asset


def sync_asset(asset):
    if not isinstance(asset, RCCClimateIndexAsset):
        asset = RCCClimateIndexAsset.objects.get(pk=asset)
    validate_source_url(asset.source_url)
    asset.last_attempted_at = timezone.now()
    asset.last_error = ""
    asset.save(update_fields=["last_attempted_at", "last_error"])
    source_url = asset.source_url
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
    existing_version = asset.versions.filter(checksum_sha256=checksum).first()
    object_name = (
        existing_version.object_name
        if existing_version
        else f"climate-indices/{asset.pk}/{checksum[:16]}.png"
    )
    storage = storages["rcc_data"]
    if not storage.exists(object_name):
        storage.save(object_name, ContentFile(data))
    with transaction.atomic():
        synced_at = timezone.now()
        asset.object_name = object_name
        asset.checksum_sha256 = checksum
        asset.size_bytes = len(data)
        asset.width = width
        asset.height = height
        asset.synced_at = synced_at
        asset.last_error = ""
        asset.save(update_fields=[
            "object_name", "checksum_sha256", "size_bytes", "width", "height",
            "synced_at", "last_error",
        ])
        RCCClimateIndexVersion.objects.get_or_create(
            asset=asset,
            checksum_sha256=checksum,
            defaults={
                "source_url": source_url, "object_name": object_name,
                "size_bytes": len(data), "width": width, "height": height,
                "synced_at": synced_at,
            },
        )
    return asset


def sync_chart(index):
    return sync_asset(legacy_asset(index))


def sync_schedule(config):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=config.interval_hours, period=IntervalSchedule.HOURS
    )
    task, _ = PeriodicTask.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "task": "climweb.pages.services.tasks.run_scheduled_rcc_climate_index_import",
            "interval": interval, "crontab": None, "solar": None, "clocked": None,
            "args": "[]", "enabled": config.enabled and RCCClimateIndexAsset.objects.filter(active=True).exists(),
            "one_off": False,
        },
    )
    return task
