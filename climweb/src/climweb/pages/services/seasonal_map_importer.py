"""Discover and safely mirror RCC seasonal climatology PNG maps."""

import hashlib
import io
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

import requests
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.db import transaction
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .models import RCCSeasonalMapAsset


CATALOGUE_URL = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "statisticalanalysis/Precipitation/Gridded_Observation/catalog.xml"
)
CATALOGUE_PATH = (
    "/thredds/catalog/ACMAD/CDD/statisticalanalysis/Precipitation/"
    "Gridded_Observation/catalog.xml"
)
SOURCE_PREFIX = "ACMAD/CDD/statisticalanalysis/Precipitation/Gridded_Observation/"
SEASONS = ("JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ", "DJF")
MAP_NAME = re.compile(r"^(0[1-9]|1[0-2])_([A-Z]{3})(?:_(1|20|50)mm)?_Afr\.png$")
MAX_PNG_BYTES = 10 * 1024 * 1024
SCHEDULE_NAME = "rcc-seasonal-maps-import"


def validate_catalogue_url(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValidationError("Invalid catalogue URL.") from exc
    allowed = getattr(settings, "RCC_SEASONAL_MAP_ALLOWED_SOURCE_HOSTS", ("sgbd.acmad.org",))
    if isinstance(allowed, str):
        allowed = [host.strip() for host in allowed.split(",")]
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in allowed
        or parsed.path != CATALOGUE_PATH
        or not parsed.netloc
        or parsed.username or parsed.password or parsed.query or parsed.fragment or port == 0
    ):
        raise ValidationError("Use the approved seasonal map THREDDS root catalogue URL.")
    return parsed


def map_details(filename):
    match = MAP_NAME.fullmatch(filename)
    if not match or SEASONS[int(match.group(1)) - 1] != match.group(2):
        raise ValidationError("Unrecognized seasonal climatology map filename.")
    return match.group(2), f"{match.group(3)}mm" if match.group(3) else "rainfall"


def source_url_for(catalogue_url, filename):
    parsed = validate_catalogue_url(catalogue_url)
    map_details(filename)
    return f"{parsed.scheme}://{parsed.netloc}/thredds/fileServer/{SOURCE_PREFIX}{filename}"


def discover_maps(catalogue_url=CATALOGUE_URL):
    validate_catalogue_url(catalogue_url)
    response = requests.get(catalogue_url, timeout=(15, 45), allow_redirects=False)
    response.raise_for_status()
    if response.status_code != 200:
        raise ValueError("The map catalogue did not return a direct response.")
    root = ElementTree.fromstring(response.content)
    names = set()
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "dataset":
            continue
        path = node.attrib.get("urlPath", "")
        if not path.startswith(SOURCE_PREFIX):
            continue
        filename = path[len(SOURCE_PREFIX):]
        try:
            map_details(filename)
        except ValidationError:
            continue
        names.add(filename)
    if not names:
        raise ValueError("No recognized seasonal maps were found in the catalogue.")
    return sorted(names)


def sync_map(catalogue_url, filename):
    season, variant = map_details(filename)
    source_url = source_url_for(catalogue_url, filename)
    with requests.get(source_url, stream=True, timeout=(15, 90), allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("The map source did not return a direct response.")
        data = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            data.extend(chunk)
            if len(data) > MAX_PNG_BYTES:
                raise ValueError("The map exceeds the size limit.")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The source is not a PNG image.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG":
                raise ValueError("The source is not a PNG image.")
            width, height = image.size
            if width * height > 25_000_000:
                raise ValueError("The map exceeds the pixel limit.")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The source PNG could not be decoded.") from exc
    checksum = hashlib.sha256(data).hexdigest()
    object_name = f"seasonal-maps/{filename[:-4]}/{checksum[:16]}.png"
    storage = storages["rcc_data"]
    if not storage.exists(object_name):
        storage.save(object_name, ContentFile(data))
    with transaction.atomic():
        asset, _ = RCCSeasonalMapAsset.objects.update_or_create(
            filename=filename,
            defaults={
                "season": season, "variant": variant, "source_url": source_url,
                "object_name": object_name, "checksum_sha256": checksum,
                "size_bytes": len(data), "width": width, "height": height,
                "synced_at": timezone.now(),
            },
        )
    return asset


def sync_schedule(config):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=config.interval_hours, period=IntervalSchedule.HOURS
    )
    task, _ = PeriodicTask.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "task": "climweb.pages.services.tasks.run_scheduled_rcc_seasonal_map_import",
            "interval": interval, "crontab": None, "solar": None, "clocked": None,
            "args": "[]", "enabled": config.enabled and bool(config.import_all_maps or config.selected_maps),
            "one_off": False,
        },
    )
    return task
