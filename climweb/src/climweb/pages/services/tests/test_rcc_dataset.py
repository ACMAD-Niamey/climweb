import hashlib
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from climweb.pages.services.models import RCCDatasetAsset


CSV_DATA = (
    b"Station,Country,Lon,Lat,Date,Precipitation\n"
    b"NIAMEY-AERO,Niger,2.16666,13.48333,2026-09-13,0\n"
    b"NIAMEY-AERO,Niger,2.16666,13.48333,2026-09-14,12.5\n"
)


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield CSV_DATA


class RCCDatasetTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_override = override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "rcc_data": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.temp_dir.name},
                },
            }
        )
        self.storage_override.enable()
        storages._storages.clear()

    def tearDown(self):
        storages._storages.clear()
        self.storage_override.disable()
        self.temp_dir.cleanup()

    def make_asset(self):
        object_name = "arc2/niger/niamey-aero/test/NIAMEY-AERO.csv"
        storages["rcc_data"].save(object_name, ContentFile(CSV_DATA))
        return RCCDatasetAsset.objects.create(
            key="arc2-niamey-aero",
            title="ARC2 daily rainfall — Niamey-Aéro",
            summary="Daily rainfall estimates.",
            station="NIAMEY-AERO",
            country="Niger",
            longitude="2.16666",
            latitude="13.48333",
            object_name=object_name,
            original_filename="NIAMEY-AERO.csv",
            checksum_sha256=hashlib.sha256(CSV_DATA).hexdigest(),
            size_bytes=len(CSV_DATA),
            record_count=2,
            coverage_start=date(2026, 9, 13),
            coverage_end=date(2026, 9, 14),
            synced_at=timezone.now(),
        )

    def make_zinder_asset(self):
        data = CSV_DATA.replace(b"NIAMEY-AERO", b"ZINDER").replace(
            b"2.16666,13.48333", b"8.98333,13.78333"
        )
        object_name = "arc2/niger/zinder/test/ZINDER.csv"
        storages["rcc_data"].save(object_name, ContentFile(data))
        return RCCDatasetAsset.objects.create(
            key="arc2-zinder",
            title="ARC2 daily rainfall — Zinder",
            summary="Daily rainfall estimates for Zinder.",
            station="ZINDER",
            country="Niger",
            longitude="8.98333",
            latitude="13.78333",
            object_name=object_name,
            original_filename="ZINDER.csv",
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            record_count=2,
            coverage_start=date(2026, 9, 13),
            coverage_end=date(2026, 9, 14),
            synced_at=timezone.now(),
        )

    def test_dataset_page_previews_local_data_without_exposing_source(self):
        asset = self.make_asset()
        asset.source_url = "http://sgbd.acmad.org:8080/private-source.csv"
        asset.save(update_fields=["source_url"])

        response = self.client.get(reverse("rcc_dataset_detail", args=[asset.key]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ARC2 daily rainfall — Niamey-Aéro")
        self.assertContains(response, "2026-09-14")
        self.assertContains(response, "12.5")
        self.assertNotContains(response, "sgbd.acmad.org")
        self.assertContains(response, 'class="rcc-dataset-toolbar"')
        self.assertNotContains(response, 'class="rcc-dataset-lead"')

    def test_category_page_lists_countries_before_stations(self):
        self.make_asset()
        self.make_zinder_asset()

        response = self.client.get(reverse("rcc_dataset_category"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_dataset_category.html")
        self.assertContains(response, "Choose a country")
        self.assertContains(response, "Niger")
        self.assertContains(response, "2 stations")
        self.assertNotContains(response, 'class="rcc-station-card"')

    def test_country_search_filters_names_and_handles_no_matches(self):
        self.make_asset()
        RCCDatasetAsset.objects.create(
            key="arc2-ghana-yendi", title="ARC2 Yendi", country="Ghana", station="YENDI",
            object_name="arc2/ghana/yendi/test/YENDI.csv", synced_at=timezone.now(),
        )
        url = reverse("rcc_dataset_category")
        response = self.client.get(url, {"q": "  nIG  "})
        self.assertContains(response, 'name="q" value="nIG"')
        self.assertContains(response, "Niger")
        self.assertNotContains(response, "Ghana")
        self.assertContains(response, "Search countries")
        response = self.client.get(url, {"q": "Kenya"})
        self.assertContains(response, "No countries match your search.")
        self.assertNotContains(response, 'class="rcc-country-card"')

    def test_country_page_lists_station_grid(self):
        self.make_asset()
        self.make_zinder_asset()

        response = self.client.get(reverse("rcc_dataset_country", args=["niger"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_dataset_country.html")
        self.assertContains(response, 'class="rcc-station-grid"')
        self.assertContains(response, "NIAMEY-AERO")
        self.assertContains(response, "ZINDER")
        self.assertContains(response, reverse("rcc_dataset_detail", args=["arc2-zinder"]))

    def test_station_search_filters_within_country(self):
        self.make_asset()
        self.make_zinder_asset()
        url = reverse("rcc_dataset_country", args=["niger"])
        response = self.client.get(url, {"q": "zind"})
        self.assertContains(response, "Search stations")
        self.assertContains(response, 'name="q" value="zind"')
        self.assertContains(response, "ZINDER")
        self.assertNotContains(response, "NIAMEY-AERO")
        response = self.client.get(url, {"q": "YENDI"})
        self.assertContains(response, "No stations match your search.")
        self.assertNotContains(response, 'class="rcc-station-card"')

    def test_download_is_served_from_rcc_storage(self):
        asset = self.make_asset()

        response = self.client.get(reverse("rcc_dataset_download", args=[asset.key]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), CSV_DATA)
        self.assertEqual(response["X-Checksum-SHA256"], asset.checksum_sha256)
        self.assertIn("NIAMEY-AERO.csv", response["Content-Disposition"])

    def test_unavailable_dataset_returns_404(self):
        RCCDatasetAsset.objects.create(key="arc2-niamey-aero", title="Not synchronized")

        response = self.client.get(reverse("rcc_dataset_detail", args=["arc2-niamey-aero"]))

        self.assertEqual(response.status_code, 404)

    @patch(
        "climweb.pages.services.management.commands.sync_rcc_arc2_station.requests.get",
        return_value=FakeResponse(),
    )
    def test_sync_validates_and_versions_the_download(self, requests_get):
        call_command("sync_rcc_arc2_niamey")

        asset = RCCDatasetAsset.objects.get(key="arc2-niamey-aero")
        self.assertEqual(asset.record_count, 2)
        self.assertEqual(asset.coverage_start, date(2026, 9, 13))
        self.assertEqual(asset.coverage_end, date(2026, 9, 14))
        self.assertEqual(asset.checksum_sha256, hashlib.sha256(CSV_DATA).hexdigest())
        self.assertTrue(storages["rcc_data"].exists(asset.object_name))
        requests_get.assert_called_once()

    def test_sync_can_import_a_local_recovery_file(self):
        source = Path(self.temp_dir.name) / "source.csv"
        source.write_bytes(CSV_DATA)

        call_command("sync_rcc_arc2_niamey", source_file=str(source))

        asset = RCCDatasetAsset.objects.get(key="arc2-niamey-aero")
        self.assertTrue(asset.is_available)
        self.assertEqual(asset.record_count, 2)

    def test_generic_importer_adds_another_station(self):
        zinder_csv = CSV_DATA.replace(b"NIAMEY-AERO", b"ZINDER").replace(
            b"2.16666,13.48333", b"8.98333,13.78333"
        )
        source = Path(self.temp_dir.name) / "zinder.csv"
        source.write_bytes(zinder_csv)

        call_command("sync_rcc_arc2_station", "ZINDER", source_file=str(source))

        asset = RCCDatasetAsset.objects.get(key="arc2-zinder")
        self.assertEqual(asset.station, "ZINDER")
        self.assertEqual(str(asset.longitude), "8.98333")
        self.assertTrue(asset.is_available)

    def test_importer_adds_another_country_without_changing_niger_keys(self):
        ghana_csv = CSV_DATA.replace(b"NIAMEY-AERO,Niger", b"YENDI,Ghana")
        source = Path(self.temp_dir.name) / "ghana.csv"
        source.write_bytes(ghana_csv)

        call_command("sync_rcc_arc2_station", "YENDI", country="Ghana", source_file=str(source))

        asset = RCCDatasetAsset.objects.get(key="arc2-ghana-yendi")
        self.assertEqual(asset.country, "Ghana")
        self.assertTrue(asset.object_name.startswith("arc2/ghana/yendi/"))
        self.assertTrue(asset.is_available)
