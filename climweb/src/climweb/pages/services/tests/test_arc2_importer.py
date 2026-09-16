from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django_celery_beat.models import PeriodicTask

from climweb.pages.services.arc2_importer import (
    catalogue_url_for,
    discover_countries,
    discover_stations,
    station_source_url,
    validate_catalogue_url,
)
from climweb.pages.services.models import RCCARC2ImportConfig, RCCARC2ImportRun
from climweb.pages.services.tasks import execute_rcc_arc2_import, run_scheduled_rcc_arc2_import


class CatalogueTests(TestCase):
    @patch("climweb.pages.services.arc2_importer.requests.get")
    def test_discovers_countries_from_parent_catalogue(self, get):
        get.return_value = Mock(content=b"""<catalog xmlns:xlink="http://www.w3.org/1999/xlink">
            <catalogRef xlink:href="Ghana/catalog.xml" />
            <catalogRef xlink:href="Niger/catalog.xml" />
            <catalogRef xlink:href="../invalid/catalog.xml" />
        </catalog>""")
        self.assertEqual(discover_countries(), ["Ghana", "Niger"])

    @patch("climweb.pages.services.arc2_importer.requests.get")
    def test_discovers_only_niger_csv_files(self, get):
        get.return_value = Mock(content=b"""<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Niger/ZINDER.csv" />
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Niger/NIAMEY-AERO.csv" />
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Ghana/ACCRA.csv" />
            <dataset urlPath="ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/Niger/../BAD.csv" />
        </catalog>""")
        self.assertEqual(discover_stations(), ["NIAMEY-AERO", "ZINDER"])

    def test_url_is_editable_but_restricted_to_approved_arc2_source(self):
        url = catalogue_url_for("Ghana")
        self.assertTrue(station_source_url(url, "Ghana", "YENDI").endswith("/Ghana/YENDI.csv"))
        with self.assertRaises(ValidationError):
            validate_catalogue_url("http://127.0.0.1/thredds/catalog/ARC2/Ghana/catalog.xml", "Ghana")
        with self.assertRaises(ValidationError):
            validate_catalogue_url(catalogue_url_for("Niger"), "Ghana")


class ImportDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("rcc-importer", "rcc@example.test", "testpass")
        self.client.force_login(self.user)
        self.config = RCCARC2ImportConfig.objects.create(
            discovered_stations=["NIAMEY-AERO", "ZINDER"], selected_stations=["NIAMEY-AERO"]
        )

    def test_save_rejects_unlisted_station(self):
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save", "stations": ["EVIL"], "interval_hours": "24", "enabled": "on",
            "catalogue_url": catalogue_url_for("Niger"),
        })
        self.assertEqual(response.status_code, 200)
        self.config.refresh_from_db()
        self.assertEqual(self.config.selected_stations, ["NIAMEY-AERO"])

    def test_schedule_and_manual_run(self):
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save", "stations": ["NIAMEY-AERO", "ZINDER"],
            "interval_hours": "12", "enabled": "on", "catalogue_url": catalogue_url_for("Niger"),
        })
        self.assertEqual(response.status_code, 302)
        schedule = PeriodicTask.objects.get(name="rcc-arc2-niger-import")
        self.assertTrue(schedule.enabled)
        self.assertEqual(schedule.interval.every, 12)
        with patch("climweb.pages.services.arc2_admin.execute_rcc_arc2_import.delay") as enqueue:
            response = self.client.post(reverse("rcc_arc2_imports"), {"action": "run"})
        self.assertEqual(response.status_code, 302)
        run = RCCARC2ImportRun.objects.get()
        self.assertEqual(run.stations, ["NIAMEY-AERO", "ZINDER"])
        enqueue.assert_called_once_with(run.pk)

    @patch("climweb.pages.services.arc2_admin.discover_stations", side_effect=ValueError("Unavailable"))
    def test_discovery_failure_preserves_selections(self, _discover):
        self.client.post(reverse("rcc_arc2_imports"), {"action": "discover"})
        self.config.refresh_from_db()
        self.assertEqual(self.config.selected_stations, ["NIAMEY-AERO"])
        self.assertEqual(self.config.discovered_stations, ["NIAMEY-AERO", "ZINDER"])

    @patch("climweb.pages.services.arc2_admin.discover_countries", return_value=["Ghana", "Niger"])
    def test_refresh_countries_preserves_existing_config(self, _discover):
        self.client.post(reverse("rcc_arc2_imports"), {"action": "discover_countries"})
        self.assertEqual(RCCARC2ImportConfig.objects.count(), 2)
        self.assertEqual(self.client.get(reverse("rcc_arc2_imports"), {"country": "Ghana"}).status_code, 200)
        self.config.refresh_from_db()
        self.assertEqual(self.config.selected_stations, ["NIAMEY-AERO"])

    def test_source_url_change_clears_stations_and_disables_schedule(self):
        self.config.enabled = True
        self.config.save(update_fields=["enabled"])
        updated_url = catalogue_url_for("Niger").replace("http://", "https://")
        response = self.client.post(reverse("rcc_arc2_imports"), {
            "action": "save", "country": "Niger", "catalogue_url": updated_url,
            "stations": ["NIAMEY-AERO"], "interval_hours": "24",
        })
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertEqual(self.config.catalogue_url, updated_url)
        self.assertEqual(self.config.selected_stations, [])
        self.assertEqual(self.config.discovered_stations, [])
        self.assertFalse(self.config.enabled)
        self.assertFalse(PeriodicTask.objects.get(name="rcc-arc2-niger-import").enabled)


class ImportTaskTests(TestCase):
    def setUp(self):
        self.config = RCCARC2ImportConfig.objects.create(
            enabled=True, selected_stations=["NIAMEY-AERO", "ZINDER"]
        )

    @patch("climweb.pages.services.tasks.call_command")
    def test_partial_failure_is_recorded_per_station(self, call_command):
        call_command.side_effect = [None, CommandError("source unavailable")]
        run = RCCARC2ImportRun.objects.create(
            config=self.config, trigger="manual", stations=["NIAMEY-AERO", "ZINDER"]
        )
        execute_rcc_arc2_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "partial")
        self.assertEqual([item["status"] for item in run.results], ["succeeded", "failed"])
        self.assertIsNotNone(run.finished_at)

    @patch("climweb.pages.services.tasks.call_command")
    def test_scheduled_run_uses_saved_selection(self, call_command):
        run_scheduled_rcc_arc2_import()
        self.assertEqual(RCCARC2ImportRun.objects.get().status, "succeeded")
        self.assertEqual(call_command.call_count, 2)
        call_command.assert_any_call(
            "sync_rcc_arc2_station", "NIAMEY-AERO", country="Niger",
            source_url=station_source_url(catalogue_url_for("Niger"), "Niger", "NIAMEY-AERO"),
        )

    @patch("climweb.pages.services.tasks.call_command")
    def test_scheduled_run_is_scoped_to_its_country(self, call_command):
        ghana = RCCARC2ImportConfig.objects.create(
            country="Ghana", catalogue_url=catalogue_url_for("Ghana"),
            enabled=True, selected_stations=["YENDI"],
        )
        run_scheduled_rcc_arc2_import(ghana.pk)
        run = RCCARC2ImportRun.objects.get()
        self.assertEqual(run.country, "Ghana")
        self.assertEqual(run.stations, ["YENDI"])
        call_command.assert_called_once_with(
            "sync_rcc_arc2_station", "YENDI", country="Ghana",
            source_url=station_source_url(catalogue_url_for("Ghana"), "Ghana", "YENDI"),
        )
