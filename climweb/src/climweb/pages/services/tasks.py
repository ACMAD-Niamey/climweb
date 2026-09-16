from celery import shared_task
from celery_singleton import Singleton
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from .models import (
    RCCARC2ImportConfig, RCCARC2ImportRun, RCCCPCImportConfig, RCCCPCImportRun,
    RCCSeasonalMapImportConfig, RCCSeasonalMapImportRun,
)
from .seasonal_map_importer import discover_maps, sync_map
from .arc2_importer import (
    discover_countries,
    discover_stations,
    split_station_id,
    station_id,
    station_source_url,
)


@shared_task(base=Singleton, unique_on=[], lock_expiry=60 * 60)
def sync_rcc_arc2_niamey():
    """Refresh the locally hosted Niamey ARC2 dataset."""
    call_command("sync_rcc_arc2_niamey")


@shared_task(base=Singleton, unique_on=["station"], lock_expiry=60 * 60)
def sync_rcc_arc2_station(station):
    """Refresh one locally hosted Niger ARC2 station dataset."""
    call_command("sync_rcc_arc2_station", station)


def create_rcc_arc2_run(config_id, trigger, requested_by=None):
    return _create_station_run(RCCARC2ImportConfig, RCCARC2ImportRun, config_id, trigger, requested_by)


def create_rcc_cpc_run(config_id, trigger, requested_by=None):
    return _create_station_run(RCCCPCImportConfig, RCCCPCImportRun, config_id, trigger, requested_by)


def _create_station_run(config_model, run_model, config_id, trigger, requested_by=None):
    with transaction.atomic():
        config = config_model.objects.select_for_update().filter(pk=config_id).first()
        if not config or not (config.import_all_stations or config.selected_stations):
            return None
        if config.runs.filter(status__in=["queued", "running"]).exists():
            return None
        return run_model.objects.create(
            config=config,
            trigger=trigger,
            stations=[] if config.import_all_stations else list(config.selected_stations),
            country="",
            catalogue_url=config.catalogue_url,
            import_all_stations=config.import_all_stations,
            requested_by=requested_by,
        )


@shared_task
def execute_rcc_arc2_import(run_id):
    _execute_station_import(RCCARC2ImportRun, "sync_rcc_arc2_station", "Synoptic_Daily_ARC2_Data", run_id)


@shared_task
def execute_rcc_cpc_import(run_id):
    _execute_station_import(RCCCPCImportRun, "sync_rcc_cpc_station", "Synoptic_Daily_CPC_Unified_Data", run_id)


def _execute_station_import(run_model, command_name, directory, run_id):
    with transaction.atomic():
        run = run_model.objects.select_for_update().get(pk=run_id)
        if run.status != "queued":
            return
        run.status = "running"
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at"])
    results = []

    def import_station(country, station):
        label = station_id(country, station)
        try:
            source_url = (
                station_source_url(run.catalogue_url, country, station)
                if directory == "Synoptic_Daily_ARC2_Data"
                else station_source_url(run.catalogue_url, country, station, directory)
            )
            call_command(command_name, station, country=country, source_url=source_url)
            results.append({"station": label, "status": "succeeded"})
        except Exception as exc:
            results.append({"station": label, "status": "failed", "error": str(exc)[:500]})
        run.results = results
        run.save(update_fields=["results"])

    if run.import_all_stations:
        try:
            countries = (
                discover_countries(run.catalogue_url)
                if directory == "Synoptic_Daily_ARC2_Data"
                else discover_countries(run.catalogue_url, directory)
            )
        except Exception as exc:
            results.append({"station": "Catalogue", "status": "failed", "error": str(exc)[:500]})
            countries = []
        for country in countries:
            try:
                stations = (
                    discover_stations(country, run.catalogue_url)
                    if directory == "Synoptic_Daily_ARC2_Data"
                    else discover_stations(country, run.catalogue_url, directory)
                )
            except Exception as exc:
                results.append({"station": country, "status": "failed", "error": str(exc)[:500]})
                run.results = results
                run.save(update_fields=["results"])
                continue
            run.stations += [station_id(country, station) for station in stations]
            run.save(update_fields=["stations"])
            for station in stations:
                import_station(country, station)
    else:
        for selected in run.stations:
            try:
                country, station = split_station_id(selected)
            except Exception as exc:
                results.append({"station": str(selected)[:100], "status": "failed", "error": str(exc)[:500]})
                continue
            import_station(country, station)
    succeeded = sum(result["status"] == "succeeded" for result in results)
    run.status = "succeeded" if succeeded and succeeded == len(results) else "partial" if succeeded else "failed"
    run.results = results
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "results", "finished_at"])


@shared_task
def run_scheduled_rcc_arc2_import(legacy_config_id=None):
    if legacy_config_id is not None:
        return  # Old per-country beat entries are retired by the migration.
    config = RCCARC2ImportConfig.objects.filter(singleton_key="arc2").first()
    if not config or not config.enabled:
        return
    run = create_rcc_arc2_run(config.pk, "scheduled")
    if run:
        execute_rcc_arc2_import(run.pk)


@shared_task
def run_scheduled_rcc_cpc_import():
    config = RCCCPCImportConfig.objects.filter(singleton_key="cpc-unified").first()
    if not config or not config.enabled:
        return
    run = create_rcc_cpc_run(config.pk, "scheduled")
    if run:
        execute_rcc_cpc_import(run.pk)


def create_rcc_seasonal_map_run(config_id, trigger, requested_by=None):
    with transaction.atomic():
        config = RCCSeasonalMapImportConfig.objects.select_for_update().filter(pk=config_id).first()
        if not config or not (config.import_all_maps or config.selected_maps):
            return None
        if config.runs.filter(status__in=["queued", "running"]).exists():
            return None
        return RCCSeasonalMapImportRun.objects.create(
            config=config, trigger=trigger, requested_by=requested_by,
            maps=[] if config.import_all_maps else list(config.selected_maps),
            catalogue_url=config.catalogue_url, import_all_maps=config.import_all_maps,
        )


@shared_task
def execute_rcc_seasonal_map_import(run_id):
    with transaction.atomic():
        run = RCCSeasonalMapImportRun.objects.select_for_update().get(pk=run_id)
        if run.status != "queued":
            return
        run.status = "running"
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at"])
    results = []
    if run.import_all_maps:
        try:
            run.maps = discover_maps(run.catalogue_url)
            run.save(update_fields=["maps"])
        except Exception as exc:
            results.append({"map": "Catalogue", "status": "failed", "error": str(exc)[:500]})
    if not results:
        for filename in run.maps:
            try:
                sync_map(run.catalogue_url, filename)
                results.append({"map": filename, "status": "succeeded"})
            except Exception as exc:
                results.append({"map": str(filename)[:80], "status": "failed", "error": str(exc)[:500]})
            run.results = results
            run.save(update_fields=["results"])
    succeeded = sum(item["status"] == "succeeded" for item in results)
    run.status = "succeeded" if succeeded == len(results) and succeeded else "partial" if succeeded else "failed"
    run.results = results
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "results", "finished_at"])


@shared_task
def run_scheduled_rcc_seasonal_map_import():
    config = RCCSeasonalMapImportConfig.objects.filter(singleton_key="seasonal-maps").first()
    if not config or not config.enabled:
        return
    run = create_rcc_seasonal_map_run(config.pk, "scheduled")
    if run:
        execute_rcc_seasonal_map_import(run.pk)
