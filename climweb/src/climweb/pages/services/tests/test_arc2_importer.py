from unittest.mock import ANY, Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django_celery_beat.models import PeriodicTask

from climweb.pages.services.arc2_importer import (
    CATALOGUE_URL,
    catalogue_url_for,
    discover_countries,
    discover_stations,
    station_source_url,
    validate_catalogue_root,
)
from climweb.pages.services.models import (
    RCCARC2ImportConfig, RCCARC2ImportLog, RCCARC2ImportRun,
    RCCCPCImportConfig, RCCCPCImportRun,
)
from climweb.pages.services.tasks import execute_rcc_arc2_import, run_scheduled_rcc_arc2_import


class CatalogueTests(TestCase):
    @patch("climweb.pages.services.arc2_importer.requests.get")
    def test_discovers_countries_from_root(self, get):
        get.return_value = Mock(content=b"""<catalog xmlns:xlink="http://www.w3.org/1999/xlink">
            <catalogRef xlink:href="Ghana/catalog.xml" />
            <catalogRef xlink:href="Niger/catalog.xml" />
            <catalogRef xlink:href="../invalid/catalog.xml" />
        </catalog>""")
        self.assertEqual(discover_countries(), ["Ghana", "Niger"])
        get.assert_called_once_with(CATALOGUE_URL, timeout=(15, 45))

    @patch("climweb.pages.services.arc2_importer.requests.get")
    def test_discovers_only_matching_country_csv_files(self, get):
        get.return_value = Mock(content=b"""<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Niger/ZINDER.csv" />
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Niger/NIAMEY-AERO.csv" />
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Ghana/ACCRA.csv" />
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Niger/../BAD.csv" />
        </catalog>""")
        self.assertEqual(discover_stations("Niger", CATALOGUE_URL), ["NIAMEY-AERO", "ZINDER"])
        get.assert_called_once_with(catalogue_url_for("Niger"), timeout=(15, 45))

    def test_root_url_is_editable_but_host_and_path_are_restricted(self):
        self.assertTrue(station_source_url(CATALOGUE_URL, "Ghana", "YENDI").endswith("/Ghana/YENDI.csv"))
        with self.assertRaises(ValidationError):
            validate_catalogue_root("http://127.0.0.1/thredds/catalog/ARC2/catalog.xml")
        with self.assertRaises(ValidationError):
            validate_catalogue_root(catalogue_url_for("Niger"))


class ImportDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("rcc-importer", "rcc@example.test", "testpass")
        self.client.force_login(self.user)
        self.config, _ = RCCARC2ImportConfig.objects.get_or_create(singleton_key="arc2")
        self.config.catalogue_url = CATALOGUE_URL
        self.config.enabled = False
        self.config.import_all_stations = False
        self.config.discovered_countries = ["Ghana", "Niger"]
        self.config.discovered_stations = ["Ghana/YENDI", "Niger/NIAMEY-AERO", "Niger/ZINDER"]
        self.config.selected_stations = ["Niger/NIAMEY-AERO"]
        self.config.save()

    def test_one_schedule_and_manual_run_use_selected_stations(self):
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save_settings", "catalogue_url": CATALOGUE_URL,
            "interval_hours": "12", "enabled": "on",
        })
        self.assertEqual(response.status_code, 302)
        schedule = PeriodicTask.objects.get(name="rcc-arc2-import")
        self.assertTrue(schedule.enabled)
        self.assertEqual(schedule.interval.every, 12)
        with patch("climweb.pages.services.arc2_admin.execute_rcc_arc2_import.delay") as enqueue:
            response = self.client.post(reverse("rcc_arc2_imports"), {"action": "run"})
        self.assertEqual(response.status_code, 302)
        run = RCCARC2ImportRun.objects.get()
        self.assertEqual(run.stations, ["Niger/NIAMEY-AERO"])
        self.assertFalse(run.import_all_stations)
        enqueue.assert_called_once_with(run.pk)

    def test_all_station_mode_can_schedule_without_selection(self):
        self.config.selected_stations = []
        self.config.save(update_fields=["selected_stations"])
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save_settings", "catalogue_url": CATALOGUE_URL,
            "interval_hours": "24", "enabled": "on", "import_all_stations": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertTrue(self.config.import_all_stations)
        self.assertTrue(PeriodicTask.objects.get(name="rcc-arc2-import").enabled)

    def test_source_url_change_clears_discovery_and_disables_schedule(self):
        updated_url = CATALOGUE_URL.replace("http://", "https://")
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save_settings", "catalogue_url": updated_url,
            "interval_hours": "24",
        })
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertEqual(self.config.catalogue_url, updated_url)
        self.assertEqual(self.config.selected_stations, [])
        self.assertEqual(self.config.discovered_countries, [])
        self.assertFalse(self.config.enabled)
        self.assertFalse(PeriodicTask.objects.get(name="rcc-arc2-import").enabled)

    def test_station_selection_is_country_scoped_and_validated(self):
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save_stations", "country": "Ghana", "stations": ["Ghana/YENDI"],
        })
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertEqual(self.config.selected_stations, ["Ghana/YENDI", "Niger/NIAMEY-AERO"])
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save_stations", "country": "Ghana", "stations": ["Ghana/EVIL"],
        })
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertEqual(self.config.selected_stations, ["Ghana/YENDI", "Niger/NIAMEY-AERO"])

    @patch("climweb.pages.services.arc2_admin.discover_countries", return_value=["Ghana", "Niger", "Togo"])
    def test_refresh_countries_preserves_selection(self, _discover):
        self.client.post(reverse("rcc_arc2_imports"), {"action": "discover_countries"})
        self.config.refresh_from_db()
        self.assertEqual(self.config.discovered_countries, ["Ghana", "Niger", "Togo"])
        self.assertEqual(self.config.selected_stations, ["Niger/NIAMEY-AERO"])

    @patch("climweb.pages.services.arc2_admin.discover_stations", return_value=["YENDI", "TEMA"])
    def test_refresh_one_country_stations(self, discover):
        self.client.post(reverse("rcc_arc2_imports"), {
            "action": "discover_stations", "country": "Ghana",
        })
        discover.assert_called_once_with("Ghana", CATALOGUE_URL)
        self.config.refresh_from_db()
        self.assertEqual(self.config.discovered_stations, [
            "Ghana/TEMA", "Ghana/YENDI", "Niger/NIAMEY-AERO", "Niger/ZINDER",
        ])

    def test_stop_queued_run_prevents_execution(self):
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", catalogue_url=CATALOGUE_URL,
            stations=["Niger/NIAMEY-AERO"],
        )
        self.assertContains(self.client.get(reverse("rcc_arc2_imports")), "Stop import")
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "stop", "run_id": str(run.pk),
        })
        self.assertEqual(response.status_code, 302)
        run.refresh_from_db()
        self.assertEqual(run.status, "cancelled")
        self.assertTrue(run.cancel_requested)
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(run.logs.get().event, "stopped")
        with patch("climweb.pages.services.tasks.call_command") as call_command:
            execute_rcc_arc2_import(run.pk)
        call_command.assert_not_called()

    def test_stop_running_run_is_scoped_to_importer(self):
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", status="running",
            catalogue_url=CATALOGUE_URL, stations=["Niger/NIAMEY-AERO"],
        )
        other_config = RCCCPCImportConfig.objects.create(singleton_key="cpc-unified")
        other = RCCCPCImportRun.objects.create(
            config=other_config, trigger="manual", status="running",
        )
        self.client.post(reverse("rcc_arc2_imports"), {"action": "stop", "run_id": str(run.pk)})
        run.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(run.cancel_requested)
        self.assertEqual(run.status, "running")
        self.assertFalse(other.cancel_requested)
        self.assertEqual(run.logs.get().event, "stop_requested")
        self.assertContains(self.client.get(reverse("rcc_arc2_imports")), "Stopping after current station")

    def test_run_log_shows_legacy_results_and_error_filter(self):
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", status="partial",
            catalogue_url=CATALOGUE_URL,
            results=[
                {"station": "Niger/NIAMEY-AERO", "status": "succeeded"},
                {"station": "Ghana/YENDI", "status": "failed", "error": "Permission denied"},
            ],
        )
        url = reverse("rcc_arc2_import_log", args=[run.pk])
        response = self.client.get(url + "?level=error")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission denied")
        self.assertNotContains(response, "Niger/NIAMEY-AERO")
        self.assertContains(response, "predates detailed logging")
        RCCARC2ImportLog.objects.create(run=run, level="warning", event="stop_requested", message="Stopping")
        response = self.client.get(url + "?source=results&level=error")
        self.assertContains(response, "Permission denied")
        self.assertContains(response, "Saved station results")

    def test_run_log_filters_and_paginates_structured_events(self):
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", status="running",
            catalogue_url=CATALOGUE_URL,
        )
        RCCARC2ImportLog.objects.bulk_create([
            RCCARC2ImportLog(run=run, level="error", event="station_failed", station=f"Niger/STATION-{number}", message=f"Error {number}")
            for number in range(101)
        ])
        url = reverse("rcc_arc2_import_log", args=[run.pk])
        response = self.client.get(url + "?level=error")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Error 100")
        self.assertContains(response, "Page 1 of 2")
        response = self.client.get(url + "?level=error&page=2")
        self.assertContains(response, "Error 0<")


class ImportTaskTests(TestCase):
    def setUp(self):
        self.config, _ = RCCARC2ImportConfig.objects.get_or_create(singleton_key="arc2")
        self.config.catalogue_url = CATALOGUE_URL
        self.config.enabled = True
        self.config.import_all_stations = False
        self.config.selected_stations = ["Niger/NIAMEY-AERO", "Ghana/YENDI"]
        self.config.save()

    @patch("climweb.pages.services.tasks.call_command")
    def test_partial_failure_is_recorded_per_station(self, call_command):
        call_command.side_effect = [None, CommandError("source unavailable")]
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", catalogue_url=CATALOGUE_URL,
            stations=["Niger/NIAMEY-AERO", "Ghana/YENDI"],
        )
        execute_rcc_arc2_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "partial")
        self.assertEqual([item["status"] for item in run.results], ["succeeded", "failed"])
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(list(run.logs.values_list("event", flat=True)), [
            "started", "station_started", "station_succeeded", "station_started", "station_failed", "finished",
        ])

    @patch("climweb.pages.services.tasks.call_command")
    def test_scheduled_run_uses_single_shared_source(self, call_command):
        run_scheduled_rcc_arc2_import()
        self.assertEqual(RCCARC2ImportRun.objects.get().status, "succeeded")
        call_command.assert_any_call(
            "sync_rcc_arc2_station", "NIAMEY-AERO", country="Niger",
            source_url=station_source_url(CATALOGUE_URL, "Niger", "NIAMEY-AERO"),
            stdout=ANY, stderr=ANY,
        )
        call_command.assert_any_call(
            "sync_rcc_arc2_station", "YENDI", country="Ghana",
            source_url=station_source_url(CATALOGUE_URL, "Ghana", "YENDI"),
            stdout=ANY, stderr=ANY,
        )

    @patch("climweb.pages.services.tasks.call_command")
    @patch("climweb.pages.services.tasks.discover_stations")
    @patch("climweb.pages.services.tasks.discover_countries", return_value=["Ghana", "Niger"])
    def test_all_station_run_discovers_every_country(self, _countries, stations, call_command):
        stations.side_effect = lambda country, root: ["YENDI"] if country == "Ghana" else ["ZINDER"]
        self.config.import_all_stations = True
        self.config.save(update_fields=["import_all_stations"])
        run_scheduled_rcc_arc2_import()
        run = RCCARC2ImportRun.objects.get()
        self.assertTrue(run.import_all_stations)
        self.assertEqual(run.stations, ["Ghana/YENDI", "Niger/ZINDER"])
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(call_command.call_count, 2)

    def test_legacy_country_schedule_does_not_start_a_global_run(self):
        run_scheduled_rcc_arc2_import(self.config.pk)
        self.assertFalse(RCCARC2ImportRun.objects.exists())

    @patch("climweb.pages.services.tasks.call_command")
    def test_stop_during_station_preserves_result_and_skips_remaining(self, call_command):
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", catalogue_url=CATALOGUE_URL,
            stations=["Niger/NIAMEY-AERO", "Ghana/YENDI"],
        )
        call_command.side_effect = lambda *args, **kwargs: RCCARC2ImportRun.objects.filter(
            pk=run.pk,
        ).update(cancel_requested=True)
        execute_rcc_arc2_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "cancelled")
        self.assertEqual(run.results, [{"station": "Niger/NIAMEY-AERO", "status": "succeeded"}])
        self.assertEqual(call_command.call_count, 1)

    @patch("climweb.pages.services.tasks.call_command")
    @patch("climweb.pages.services.tasks.discover_stations", return_value=["YENDI", "TEMA"])
    @patch("climweb.pages.services.tasks.discover_countries", return_value=["Ghana", "Niger"])
    def test_stop_all_station_run_skips_later_stations_and_countries(self, countries, stations, call_command):
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", catalogue_url=CATALOGUE_URL,
            import_all_stations=True,
        )
        call_command.side_effect = lambda *args, **kwargs: RCCARC2ImportRun.objects.filter(
            pk=run.pk,
        ).update(cancel_requested=True)
        execute_rcc_arc2_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "cancelled")
        self.assertEqual(call_command.call_count, 1)
        stations.assert_called_once_with("Ghana", CATALOGUE_URL)
