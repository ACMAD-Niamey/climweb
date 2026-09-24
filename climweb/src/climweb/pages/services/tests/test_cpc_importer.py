import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django_celery_beat.models import PeriodicTask

from climweb.pages.services.cpc_importer import CATALOGUE_URL, DIRECTORY, validate_catalogue_root
from climweb.pages.services.models import RCCCPCImportConfig, RCCCPCImportRun, RCCDatasetAsset
from climweb.pages.services.tasks import execute_rcc_cpc_import


CSV_DATA = (
    "Station,Country,Lon,Lat,Date,Precipitation\n"
    "NIAMEY-AERO,Niger,2.16666,13.48333,2026-09-13,0\n"
    "NIAMEY-AERO,Niger,2.16666,13.48333,2026-09-14,12.5\n"
)


class CPCImporterTests(TestCase):
    def test_importer_index_lists_both_management_pages(self):
        user = get_user_model().objects.create_superuser("rcc-index", "index@example.test", "testpass")
        self.client.force_login(user)
        RCCCPCImportConfig.objects.create(
            selected_stations=["Niger/NIAMEY-AERO"], enabled=False,
        )
        response = self.client.get(reverse("rcc_imports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ARC2 daily station rainfall")
        self.assertContains(response, "CPC-Unified estimated daily rainfall")
        self.assertContains(response, reverse("rcc_arc2_imports"))
        self.assertContains(response, reverse("rcc_cpc_imports"))
        self.assertContains(response, "1 selected station")

    def test_rejects_arc2_catalogue(self):
        with self.assertRaises(ValidationError):
            validate_catalogue_root(CATALOGUE_URL.replace(DIRECTORY, "Synoptic_Daily_ARC2_Data"))

    def test_manual_run_uses_cpc_source_and_command(self):
        config = RCCCPCImportConfig.objects.create(
            selected_stations=["Niger/NIAMEY-AERO"], catalogue_url=CATALOGUE_URL
        )
        run = RCCCPCImportRun.objects.create(
            config=config, trigger="manual", stations=config.selected_stations,
            catalogue_url=CATALOGUE_URL,
        )
        with patch("climweb.pages.services.tasks.call_command") as command:
            execute_rcc_cpc_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(command.call_args.args[:2], ("sync_rcc_cpc_station", "NIAMEY-AERO"))
        self.assertIn(DIRECTORY, command.call_args.kwargs["source_url"])

    def test_dashboard_keeps_cpc_schedule_off_by_default(self):
        user = get_user_model().objects.create_superuser("cpc-importer", "cpc@example.test", "testpass")
        self.client.force_login(user)
        response = self.client.get(reverse("rcc_cpc_imports"))
        self.assertContains(response, "CPC-Unified")
        config = RCCCPCImportConfig.objects.get()
        self.assertFalse(config.enabled)
        response = self.client.post(reverse("rcc_cpc_imports"), {
            "action": "save_settings", "catalogue_url": CATALOGUE_URL,
            "interval_hours": "24",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PeriodicTask.objects.get(name="rcc-cpc-unified-import").enabled)

    def test_local_command_and_browse(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "rcc_data": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": temp_dir},
                },
            }):
                storages._storages.clear()
                source = Path(temp_dir) / "cpc.csv"
                source.write_text(CSV_DATA)
                try:
                    call_command("sync_rcc_cpc_station", "NIAMEY-AERO", source_file=str(source))
                    asset = RCCDatasetAsset.objects.get(key="cpc-unified-niger-niamey-aero")
                    self.assertTrue(asset.object_name.startswith("cpc-unified/niger/"))
                    category = self.client.get(reverse("rcc_cpc_dataset_category"))
                    self.assertContains(category, "Niger")
                    self.assertContains(category, "Climate Monitoring")
                    self.assertContains(category, 'data-country-select')
                    self.assertContains(category, 'data-station-select')
                    self.assertContains(category, "NIAMEY-AERO")
                    self.assertNotContains(category, "rcc-country-card")
                    self.assertNotContains(category, "Search countries")
                    country = self.client.get(reverse("rcc_cpc_dataset_country", args=["niger"]))
                    self.assertContains(country, "NIAMEY-AERO")
                    self.assertContains(country, "Search stations")
                    self.assertContains(
                        self.client.get(reverse("rcc_cpc_dataset_country", args=["niger"]), {"q": "zinder"}),
                        "No stations match your search.",
                    )
                    detail = self.client.get(reverse("rcc_dataset_detail", args=[asset.key]))
                    self.assertContains(detail, "CPC-Unified")
                finally:
                    storages._storages.clear()

    def test_malformed_source_precipitation_is_blanked_and_disclosed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "corrupt.csv"
            source.write_text(CSV_DATA.replace("2026-09-14,12.5", "2026-09-14,forrtl: severe SIGSEGV"))
            with override_settings(STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "rcc_data": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": temp_dir},
                },
            }):
                storages._storages.clear()
                try:
                    call_command("sync_rcc_cpc_station", "NIAMEY-AERO", source_file=str(source))
                    asset = RCCDatasetAsset.objects.get(key="cpc-unified-niger-niamey-aero")
                    self.assertIn("1 non-numeric", asset.summary)
                    with storages["rcc_data"].open(asset.object_name) as hosted:
                        self.assertIn(b"2026-09-14,\r\n", hosted.read())
                    self.assertIn("forrtl", source.read_text())  # Source file was not modified.
                finally:
                    storages._storages.clear()
