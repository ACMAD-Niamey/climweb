"""CPC-Unified catalogue access and its independent import schedule."""

from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .arc2_importer import (
    discover_countries as _discover_countries,
    discover_stations as _discover_stations,
    validate_catalogue_root as _validate_catalogue_root,
)


CATALOGUE_URL = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatedataservice/Synoptic_Daily_CPC_Unified_Data/catalog.xml"
)
DIRECTORY = "Synoptic_Daily_CPC_Unified_Data"
SCHEDULE_NAME = "rcc-cpc-unified-import"


def validate_catalogue_root(url):
    return _validate_catalogue_root(url, DIRECTORY)


def discover_countries(root_url=CATALOGUE_URL):
    return _discover_countries(root_url, DIRECTORY)


def discover_stations(country="Niger", root_url=CATALOGUE_URL):
    return _discover_stations(country, root_url, DIRECTORY)


def sync_schedule(config):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=config.interval_hours, period=IntervalSchedule.HOURS
    )
    task, _ = PeriodicTask.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "task": "climweb.pages.services.tasks.run_scheduled_rcc_cpc_import",
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
