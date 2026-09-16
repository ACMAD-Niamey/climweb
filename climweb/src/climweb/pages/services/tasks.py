from celery import shared_task
from celery_singleton import Singleton
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from .models import RCCARC2ImportConfig, RCCARC2ImportRun
from .arc2_importer import catalogue_url_for, station_source_url


@shared_task(base=Singleton, unique_on=[], lock_expiry=60 * 60)
def sync_rcc_arc2_niamey():
    """Refresh the locally hosted Niamey ARC2 dataset."""
    call_command("sync_rcc_arc2_niamey")


@shared_task(base=Singleton, unique_on=["station"], lock_expiry=60 * 60)
def sync_rcc_arc2_station(station):
    """Refresh one locally hosted Niger ARC2 station dataset."""
    call_command("sync_rcc_arc2_station", station)


def create_rcc_arc2_run(config_id, trigger, requested_by=None):
    with transaction.atomic():
        config = RCCARC2ImportConfig.objects.select_for_update().filter(pk=config_id).first()
        if not config or not config.selected_stations:
            return None
        if config.runs.filter(status__in=["queued", "running"]).exists():
            return None
        return RCCARC2ImportRun.objects.create(
            config=config,
            trigger=trigger,
            stations=list(config.selected_stations),
            country=config.country,
            catalogue_url=config.catalogue_url,
            requested_by=requested_by,
        )


@shared_task
def execute_rcc_arc2_import(run_id):
    run = RCCARC2ImportRun.objects.get(pk=run_id)
    if run.status != "queued":
        return
    run.status = "running"
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])
    results = []
    for station in run.stations:
        try:
            source_url = station_source_url(
                run.catalogue_url or catalogue_url_for(run.country), run.country, station
            )
            call_command("sync_rcc_arc2_station", station, country=run.country, source_url=source_url)
            results.append({"station": station, "status": "succeeded"})
        except Exception as exc:
            results.append({"station": station, "status": "failed", "error": str(exc)[:500]})
        run.results = results
        run.save(update_fields=["results"])
    succeeded = sum(result["status"] == "succeeded" for result in results)
    run.status = "succeeded" if succeeded == len(results) else "partial" if succeeded else "failed"
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "finished_at"])


@shared_task
def run_scheduled_rcc_arc2_import(config_id=None):
    config = (
        RCCARC2ImportConfig.objects.filter(pk=config_id).first()
        if config_id is not None
        else RCCARC2ImportConfig.objects.filter(country="Niger").first()
    )
    if not config or not config.enabled:
        return
    run = create_rcc_arc2_run(config.pk, "scheduled")
    if run:
        execute_rcc_arc2_import(run.pk)
