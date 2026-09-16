import hashlib
import io
import tempfile

from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from climweb.pages.services.models import RCCSeasonalMapAsset


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (12, 8), "green").save(output, format="PNG")
    return output.getvalue()


class SeasonalMapGalleryTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_override = override_settings(STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            "rcc_data": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
                "OPTIONS": {"location": self.temp_dir.name},
            },
        })
        self.storage_override.enable()
        storages._storages.clear()

    def tearDown(self):
        storages._storages.clear()
        self.storage_override.disable()
        self.temp_dir.cleanup()

    def make_map(self, filename, season, variant, store=True):
        data = png_bytes()
        object_name = f"seasonal-maps/{filename}/test.png"
        if store:
            storages["rcc_data"].save(object_name, ContentFile(data))
        return RCCSeasonalMapAsset.objects.create(
            filename=filename, season=season, variant=variant,
            source_url=f"http://sgbd.acmad.org/source/{filename}",
            object_name=object_name, checksum_sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data), width=12, height=8, synced_at=timezone.now(),
        )

    def test_gallery_has_empty_state_then_lists_and_filters_maps(self):
        gallery_url = reverse("rcc_seasonal_map_gallery")
        self.assertContains(self.client.get(gallery_url), "Maps are being prepared")
        jfm = self.make_map("01_JFM_Afr.png", "JFM", "rainfall")
        self.make_map("02_FMA_20mm_Afr.png", "FMA", "20mm")

        response = self.client.get(gallery_url)
        self.assertContains(response, "JFM — Mean rainfall")
        self.assertContains(response, "FMA — Days above 20 mm")
        self.assertContains(response, reverse("rcc_seasonal_map_file", args=[jfm.pk]))
        self.assertNotContains(response, "sgbd.acmad.org")

        filtered = self.client.get(gallery_url, {"season": "JFM", "type": "rainfall"})
        self.assertContains(filtered, "JFM — Mean rainfall")
        self.assertNotContains(filtered, "FMA — Days above 20 mm")
        no_match = self.client.get(gallery_url, {"season": "DJF", "type": "rainfall"})
        self.assertContains(no_match, "No maps match these filters")

    def test_public_image_and_download_serve_local_storage_only(self):
        asset = self.make_map("01_JFM_Afr.png", "JFM", "rainfall")
        url = reverse("rcc_seasonal_map_file", args=[asset.pk])
        image = self.client.get(url)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/png")
        self.assertEqual(b"".join(image.streaming_content), png_bytes())
        self.assertEqual(image["X-Checksum-SHA256"], asset.checksum_sha256)
        download = self.client.get(url, {"download": "1"})
        self.assertIn("attachment", download["Content-Disposition"])
        self.assertIn(asset.filename, download["Content-Disposition"])
        self.assertEqual(self.client.get(reverse("rcc_seasonal_map_file", args=[9999])).status_code, 404)

    def test_missing_stored_image_returns_404(self):
        asset = self.make_map("01_JFM_Afr.png", "JFM", "rainfall", store=False)
        self.assertEqual(self.client.get(reverse("rcc_seasonal_map_file", args=[asset.pk])).status_code, 404)
