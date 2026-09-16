import io
import tempfile
from unittest.mock import Mock, patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from django.urls import reverse
from django_celery_beat.models import PeriodicTask

from climweb.pages.services.models import (
    RCCSeasonalMapAsset, RCCSeasonalMapImportConfig, RCCSeasonalMapImportRun,
)
from climweb.pages.services.seasonal_map_importer import (
    CATALOGUE_URL, discover_maps, source_url_for, sync_map, validate_catalogue_url,
)
from climweb.pages.services.tasks import create_rcc_seasonal_map_run, execute_rcc_seasonal_map_import


class MapResponse:
    status_code = 200

    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.content


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (12, 8), "green").save(output, format="PNG")
    return output.getvalue()


class SeasonalMapImporterTests(TestCase):
    def test_catalogue_discovers_only_expected_map_names(self):
        xml = b'''<catalog>
          <dataset urlPath="ACMAD/CDD/statisticalanalysis/Precipitation/Gridded_Observation/01_JFM_Afr.png" />
          <dataset urlPath="ACMAD/CDD/statisticalanalysis/Precipitation/Gridded_Observation/01_JFM_20mm_Afr.png" />
          <dataset urlPath="ACMAD/CDD/statisticalanalysis/Precipitation/Gridded_Observation/../../evil.png" />
          <dataset urlPath="ACMAD/CDD/statisticalanalysis/Precipitation/Gridded_Observation/02_JFM_Afr.png" />
        </catalog>'''
        with patch("climweb.pages.services.seasonal_map_importer.requests.get", return_value=MapResponse(xml)) as get:
            self.assertEqual(discover_maps(), ["01_JFM_20mm_Afr.png", "01_JFM_Afr.png"])
        get.assert_called_once_with(CATALOGUE_URL, timeout=(15, 45), allow_redirects=False)
        with self.assertRaises(ValidationError):
            validate_catalogue_url(CATALOGUE_URL.replace("sgbd.acmad.org", "127.0.0.1"))
        with self.assertRaises(ValidationError):
            source_url_for(CATALOGUE_URL, "../evil.png")

    def test_png_is_validated_and_stored_idempotently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "rcc_data": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": temp_dir}},
            }):
                storages._storages.clear()
                try:
                    with patch("climweb.pages.services.seasonal_map_importer.requests.get", return_value=MapResponse(png_bytes())):
                        first = sync_map(CATALOGUE_URL, "01_JFM_Afr.png")
                        second = sync_map(CATALOGUE_URL, "01_JFM_Afr.png")
                    self.assertEqual(first.pk, second.pk)
                    self.assertEqual((second.season, second.variant, second.width, second.height), ("JFM", "rainfall", 12, 8))
                    self.assertTrue(storages["rcc_data"].exists(second.object_name))
                    preview_url = reverse("rcc_seasonal_map_preview", args=[second.pk])
                    self.assertEqual(self.client.get(preview_url).status_code, 302)
                    user = get_user_model().objects.create_superuser("map-preview", "preview@example.test", "testpass")
                    self.client.force_login(user)
                    preview = self.client.get(preview_url)
                    self.assertEqual(preview.status_code, 200)
                    self.assertEqual(preview["Content-Type"], "image/png")
                    self.assertEqual(b"".join(preview.streaming_content), png_bytes())
                    with patch("climweb.pages.services.seasonal_map_importer.requests.get", return_value=MapResponse(b"not a png")):
                        with self.assertRaisesMessage(ValueError, "not a PNG"):
                            sync_map(CATALOGUE_URL, "02_FMA_Afr.png")
                    self.assertEqual(RCCSeasonalMapAsset.objects.count(), 1)
                finally:
                    storages._storages.clear()

    def test_dashboard_and_manual_run_keep_schedule_disabled(self):
        user = get_user_model().objects.create_superuser("map-admin", "maps@example.test", "testpass")
        self.client.force_login(user)
        index = self.client.get(reverse("rcc_imports"))
        self.assertContains(index, "Seasonal rainfall climatology maps")
        self.assertContains(index, reverse("rcc_seasonal_map_imports"))
        dashboard = self.client.get(reverse("rcc_seasonal_map_imports"))
        self.assertEqual(dashboard.status_code, 200)
        config = RCCSeasonalMapImportConfig.objects.get()
        self.assertFalse(config.enabled)
        with patch("climweb.pages.services.seasonal_map_admin.discover_maps", return_value=["01_JFM_Afr.png"]):
            self.client.post(reverse("rcc_seasonal_map_imports"), {"action": "discover"})
        response = self.client.post(reverse("rcc_seasonal_map_imports"), {
            "action": "save_maps", "maps": ["01_JFM_Afr.png"],
        })
        self.assertEqual(response.status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.selected_maps, ["01_JFM_Afr.png"])
        self.assertFalse(PeriodicTask.objects.get(name="rcc-seasonal-maps-import").enabled)
        with patch("climweb.pages.services.seasonal_map_admin.execute_rcc_seasonal_map_import.delay") as enqueue:
            self.client.post(reverse("rcc_seasonal_map_imports"), {"action": "run"})
        run = RCCSeasonalMapImportRun.objects.get()
        self.assertEqual(run.maps, ["01_JFM_Afr.png"])
        enqueue.assert_called_once_with(run.pk)

    def test_run_records_failed_map_without_losing_other_results(self):
        config = RCCSeasonalMapImportConfig.objects.create(
            selected_maps=["01_JFM_Afr.png", "02_FMA_Afr.png"]
        )
        run = create_rcc_seasonal_map_run(config.pk, "manual")
        with patch("climweb.pages.services.tasks.sync_map", side_effect=[Mock(), ValueError("bad PNG")]):
            execute_rcc_seasonal_map_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "partial")
        self.assertEqual([item["status"] for item in run.results], ["succeeded", "failed"])
