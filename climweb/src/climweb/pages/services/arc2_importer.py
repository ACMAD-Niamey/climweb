"""ARC2 catalogue discovery, URL safety, and the shared import schedule."""

import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .models import RCCARC2ImportConfig


CATALOGUE_URL = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatedataservice/Synoptic_Daily_ARC2_Data/catalog.xml"
)
COUNTRY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
STATION_PATTERN = re.compile(r"^[A-Z0-9_-]+$")
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
SCHEDULE_NAME = "rcc-arc2-import"
ARC2_DIRECTORY = "Synoptic_Daily_ARC2_Data"


def _validated_url(url, service):
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
        raise ValidationError("The URL must use a THREDDS catalogue or fileServer path.")
    return parsed, parsed.path[len(prefix):]


def validate_catalogue_root(url, directory=ARC2_DIRECTORY):
    parsed, path = _validated_url(url, "catalog")
    if not path.endswith(f"/{directory}/catalog.xml"):
        raise ValidationError("Use the dataset root catalog.xml URL, above the country directories.")
    return parsed, path[: -len("catalog.xml")]


def validate_catalogue_url(url, country, directory=ARC2_DIRECTORY):
    if not COUNTRY_PATTERN.fullmatch(country):
        raise ValidationError("Invalid ARC2 country name.")
    parsed, path = _validated_url(url, "catalog")
    if not path.endswith(f"/{directory}/{country}/catalog.xml"):
        raise ValidationError("The catalogue URL must point to this country's dataset catalog.xml.")
    return parsed, path[: -len("catalog.xml")]


def catalogue_url_for(country, root_url=CATALOGUE_URL, directory=ARC2_DIRECTORY):
    if not COUNTRY_PATTERN.fullmatch(country):
        raise ValidationError("Invalid ARC2 country name.")
    validate_catalogue_root(root_url, directory)
    return f"{root_url[:-len('catalog.xml')]}{country}/catalog.xml"


def station_source_url(root_url, country, station, directory=ARC2_DIRECTORY):
    if not STATION_PATTERN.fullmatch(station):
        raise ValidationError("Invalid ARC2 station name.")
    try:
        parsed, source_prefix = validate_catalogue_root(root_url, directory)
    except ValidationError:
        # Keep the station management command's historical country URL usable.
        parsed, source_prefix = validate_catalogue_url(root_url, country, directory)
    else:
        if not COUNTRY_PATTERN.fullmatch(country):
            raise ValidationError("Invalid ARC2 country name.")
        source_prefix += f"{country}/"
    return f"{parsed.scheme}://{parsed.netloc}/thredds/fileServer/{source_prefix}{station}.csv"


def validate_station_source_url(url, country, station, directory=ARC2_DIRECTORY):
    if not COUNTRY_PATTERN.fullmatch(country) or not STATION_PATTERN.fullmatch(station):
        raise ValidationError("Invalid ARC2 country or station name.")
    _, path = _validated_url(url, "fileServer")
    if not path.endswith(f"/{directory}/{country}/{station}.csv"):
        raise ValidationError("The source URL does not match this dataset country and station.")


def station_id(country, station):
    if not COUNTRY_PATTERN.fullmatch(country) or not STATION_PATTERN.fullmatch(station):
        raise ValidationError("Invalid ARC2 country or station name.")
    return f"{country}/{station}"


def split_station_id(value):
    try:
        country, station = value.split("/", 1)
    except (AttributeError, ValueError) as exc:
        raise ValidationError("Invalid ARC2 station selection.") from exc
    station_id(country, station)
    return country, station


def discover_countries(root_url=CATALOGUE_URL, directory=ARC2_DIRECTORY):
    validate_catalogue_root(root_url, directory)
    response = requests.get(root_url, timeout=(15, 45))
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


def discover_stations(country="Niger", root_url=CATALOGUE_URL, directory=ARC2_DIRECTORY):
    country_url = catalogue_url_for(country, root_url, directory)
    _, source_prefix = validate_catalogue_url(country_url, country, directory)
    response = requests.get(country_url, timeout=(15, 45))
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
    for old_task in PeriodicTask.objects.filter(
        name__startswith="rcc-arc2-", name__endswith="-import", enabled=True
    ).exclude(name=SCHEDULE_NAME):
        old_task.enabled = False
        old_task.save(update_fields=["enabled"])
    task, _ = PeriodicTask.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "task": "climweb.pages.services.tasks.run_scheduled_rcc_arc2_import",
            "interval": interval,
            "crontab": None,
            "solar": None,
            "clocked": None,
            "args": "[]",
            "enabled": config.enabled and bool(config.import_all_stations or config.selected_stations),
            "one_off": False,
        },
    )
    return task
