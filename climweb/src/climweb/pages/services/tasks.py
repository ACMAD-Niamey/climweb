import logging
from io import StringIO

from celery import shared_task
from celery_singleton import Singleton
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from .models import (
    RCCARC2ImportConfig, RCCARC2ImportRun, RCCCPCImportConfig, RCCCPCImportRun,
    RCCSeasonalMapImportConfig, RCCSeasonalMapImportRun,
    RCCEIN15ImportConfig, RCCEIN15ImportRun,
)
from .seasonal_map_importer import discover_maps, sync_map
from .ein15_importer import sync_file as sync_ein15_file
from .arc2_importer import (
    discover_countries,
    discover_stations,
    split_station_id,
    station_id,
    station_source_url,
)


logger = logging.getLogger(__name__)


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
        run = run_model.objects.create(
            config=config,
            trigger=trigger,
            stations=[] if config.import_all_stations else list(config.selected_stations),
            country="",
            catalogue_url=config.catalogue_url,
            import_all_stations=config.import_all_stations,
            requested_by=requested_by,
        )
        run.logs.create(
            level="info", event="queued",
            message=f"{trigger.title()} import queued for {'all stations' if run.import_all_stations else f'{len(run.stations)} selected stations'}.",
        )
        return run


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

    def record_log(level, event, station="", message=""):
        run.logs.create(
            level=level, event=event, station=station[:150], message=str(message)[:1000],
        )
        log_method = logger.error if level == "error" else logger.warning if level == "warning" else logger.info
        log_method("RCC %s run %s %s %s: %s", directory, run_id, event, station, message)

    record_log("info", "started", message="Import worker started.")

    def stopping():
        return run_model.objects.filter(pk=run_id, cancel_requested=True).exists()

    def import_station(country, station):
        label = station_id(country, station)
        record_log("info", "station_started", station=label, message="Downloading and validating station CSV.")
        try:
            source_url = (
                station_source_url(run.catalogue_url, country, station)
                if directory == "Synoptic_Daily_ARC2_Data"
                else station_source_url(run.catalogue_url, country, station, directory)
            )
            output = StringIO()
            call_command(command_name, station, country=country, source_url=source_url, stdout=output, stderr=output)
            results.append({"station": label, "status": "succeeded"})
            summary = output.getvalue().strip().splitlines()
            record_log("success", "station_succeeded", station=label, message=summary[-1] if summary else "Station synchronized.")
        except Exception as exc:
            results.append({"station": label, "status": "failed", "error": str(exc)[:500]})
            record_log("error", "station_failed", station=label, message=f"{type(exc).__name__}: {exc}")
        run.results = results
        run.save(update_fields=["results"])

    if run.import_all_stations and not stopping():
        try:
            countries = (
                discover_countries(run.catalogue_url)
                if directory == "Synoptic_Daily_ARC2_Data"
                else discover_countries(run.catalogue_url, directory)
            )
            record_log("info", "countries_discovered", message=f"Discovered {len(countries)} countries.")
        except Exception as exc:
            results.append({"station": "Catalogue", "status": "failed", "error": str(exc)[:500]})
            record_log("error", "catalogue_failed", message=f"{type(exc).__name__}: {exc}")
            countries = []
        for country in countries:
            if stopping():
                break
            try:
                stations = (
                    discover_stations(country, run.catalogue_url)
                    if directory == "Synoptic_Daily_ARC2_Data"
                    else discover_stations(country, run.catalogue_url, directory)
                )
            except Exception as exc:
                results.append({"station": country, "status": "failed", "error": str(exc)[:500]})
                record_log("error", "country_failed", station=country, message=f"{type(exc).__name__}: {exc}")
                run.results = results
                run.save(update_fields=["results"])
                continue
            record_log("info", "stations_discovered", station=country, message=f"Discovered {len(stations)} stations.")
            run.stations += [station_id(country, station) for station in stations]
            run.save(update_fields=["stations"])
            for station in stations:
                if stopping():
                    break
                import_station(country, station)
    elif not run.import_all_stations:
        for selected in run.stations:
            if stopping():
                break
            try:
                country, station = split_station_id(selected)
            except Exception as exc:
                results.append({"station": str(selected)[:100], "status": "failed", "error": str(exc)[:500]})
                record_log("error", "selection_failed", station=str(selected), message=f"{type(exc).__name__}: {exc}")
                continue
            import_station(country, station)
    succeeded = sum(result["status"] == "succeeded" for result in results)
    with transaction.atomic():
        run = run_model.objects.select_for_update().get(pk=run_id)
        run.status = (
            "cancelled" if run.cancel_requested else
            "succeeded" if succeeded and succeeded == len(results) else
            "partial" if succeeded else "failed"
        )
        run.results = results
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "results", "finished_at"])
    record_log(
        "warning" if run.status == "cancelled" else "info",
        "finished", message=f"{run.get_status_display()}: {succeeded} succeeded, {len(results) - succeeded} failed.",
    )


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


def create_rcc_ein15_run(config_id, trigger, requested_by=None):
    with transaction.atomic():
        config = RCCEIN15ImportConfig.objects.select_for_update().filter(pk=config_id).first()
        if not config:
            return None
        discovered = {item["filename"] for item in config.discovered_files}
        files = sorted(set(config.selected_files) & discovered)
        if not files or config.runs.filter(status__in=["queued", "running"]).exists():
            return None
        return RCCEIN15ImportRun.objects.create(
            config=config, trigger=trigger, requested_by=requested_by,
            files=files, catalogue_url=config.catalogue_url,
        )


@shared_task
def execute_rcc_ein15_import(run_id):
    with transaction.atomic():
        run = RCCEIN15ImportRun.objects.select_for_update().get(pk=run_id)
        if run.status != "queued":
            return
        run.status = "running"
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at"])
    results = []
    for filename in run.files:
        try:
            sync_ein15_file(run.catalogue_url, filename)
            results.append({"file": filename, "status": "succeeded"})
        except Exception as exc:
            results.append({"file": str(filename)[:100], "status": "failed", "error": str(exc)[:500]})
        run.results = results
        run.save(update_fields=["results"])
    succeeded = sum(item["status"] == "succeeded" for item in results)
    run.status = "succeeded" if succeeded == len(results) and succeeded else "partial" if succeeded else "failed"
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "results", "finished_at"])


@shared_task
def run_scheduled_rcc_ein15_import():
    config = RCCEIN15ImportConfig.objects.filter(singleton_key="ein15").first()
    if not config or not config.enabled:
        return
    run = create_rcc_ein15_run(config.pk, "scheduled")
    if run:
        execute_rcc_ein15_import(run.pk)
