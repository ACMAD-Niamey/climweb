"""Country discovery, validated THREDDS URLs, and ARC2 schedules."""

import json
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .models import RCCARC2ImportConfig


CATALOGUE_ROOT = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatedataservice/Synoptic_Daily_ARC2_Data"
)
COUNTRY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
STATION_PATTERN = re.compile(r"^[A-Z0-9_-]+$")
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def catalogue_url_for(country):
    if not COUNTRY_PATTERN.fullmatch(country):
        raise ValueError("Invalid ARC2 country name.")
    return f"{CATALOGUE_ROOT}/{country}/catalog.xml"


def _validated_url(url, service, country):
    if not COUNTRY_PATTERN.fullmatch(country):
        raise ValidationError("Invalid ARC2 country name.")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValidationError("Invalid source URL.") from exc
    allowed = getattr(settings, "RCC_ARC2_ALLOWED_SOURCE_HOSTS", ("sgbd.acmad.org",))
    if isinstance(allowed, str):
        allowed = [host.strip() for host in allowed.split(",")]
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in allowed
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or port == 0
    ):
        raise ValidationError("Use an allow-listed THREDDS host without credentials or query parameters.")
    prefix = f"/thredds/{service}/"
    if not parsed.path.startswith(prefix):
        raise ValidationError("The URL must use the THREDDS catalogue or fileServer path.")
    return parsed, parsed.path[len(prefix):]


def validate_catalogue_url(url, country):
    parsed, path = _validated_url(url, "catalog", country)
    if not path.endswith(f"/Synoptic_Daily_ARC2_Data/{country}/catalog.xml"):
        raise ValidationError("The catalogue URL must point to this country's ARC2 catalog.xml.")
    return parsed, path[: -len("catalog.xml")]


def station_source_url(catalogue_url, country, station):
    if not STATION_PATTERN.fullmatch(station):
        raise ValidationError("Invalid ARC2 station name.")
    parsed, source_prefix = validate_catalogue_url(catalogue_url, country)
    return f"{parsed.scheme}://{parsed.netloc}/thredds/fileServer/{source_prefix}{station}.csv"


def validate_station_source_url(url, country, station):
    _, path = _validated_url(url, "fileServer", country)
    if not path.endswith(f"/Synoptic_Daily_ARC2_Data/{country}/{station}.csv"):
        raise ValidationError("The source URL does not match this ARC2 country and station.")


def discover_countries():
    response = requests.get(f"{CATALOGUE_ROOT}/catalog.xml", timeout=(15, 45))
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    countries = set()
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "catalogRef":
            continue
        href = node.attrib.get(XLINK_HREF, "")
        if href.endswith("/catalog.xml"):
            country = href[: -len("/catalog.xml")]
            if COUNTRY_PATTERN.fullmatch(country):
                countries.add(country)
    if not countries:
        raise ValueError("The ARC2 catalogue contains no country directories.")
    return sorted(countries)


def discover_stations(country="Niger", catalogue_url=None):
    catalogue_url = catalogue_url or catalogue_url_for(country)
    _, source_prefix = validate_catalogue_url(catalogue_url, country)
    response = requests.get(catalogue_url, timeout=(15, 45))
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    stations = set()
    for dataset in root.iter():
        if dataset.tag.rsplit("}", 1)[-1] != "dataset":
            continue
        path = dataset.attrib.get("urlPath", "")
        if path.startswith(source_prefix):
            filename = path[len(source_prefix):]
            if filename.endswith(".csv") and STATION_PATTERN.fullmatch(filename[:-4]):
                stations.add(filename[:-4])
    if not stations:
        raise ValueError(f"The {country} ARC2 catalogue contains no valid station CSV files.")
    return sorted(stations)


def sync_schedule(config: RCCARC2ImportConfig):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=config.interval_hours, period=IntervalSchedule.HOURS
    )
    task, _ = PeriodicTask.objects.update_or_create(
        name=f"rcc-arc2-{slugify(config.country)}-import",
        defaults={
            "task": "climweb.pages.services.tasks.run_scheduled_rcc_arc2_import",
            "interval": interval,
            "crontab": None,
            "solar": None,
            "clocked": None,
            "args": json.dumps([config.pk]),
            "enabled": config.enabled and bool(config.selected_stations),
            "one_off": False,
        },
    )
    return task
