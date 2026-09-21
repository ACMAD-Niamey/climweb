import hashlib
import io
import tempfile
from unittest.mock import patch

from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from climweb.pages.services.climate_index_importer import SOURCE_ROOT, chart_details, sync_chart
from climweb.pages.services.models import RCCClimateIndexAsset


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (16, 10), "navy").save(output, format="PNG")
    return output.getvalue()


class ChartResponse:
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


class ClimateIndexGalleryTests(TestCase):
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

    def make_asset(self, index, scope, title):
        data = png_bytes()
        object_name = f"climate-indices/hs_hg{index}/test.png"
        storages["rcc_data"].save(object_name, ContentFile(data))
        return RCCClimateIndexAsset.objects.create(
            legacy_index=index,
            title=title,
            scope=scope,
            source_url=f"{SOURCE_ROOT}/hs_hg{index}.png",
            object_name=object_name,
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            width=16,
            height=10,
            synced_at=timezone.now(),
        )

    def test_import_validates_png_and_updates_asset_idempotently(self):
        with patch(
            "climweb.pages.services.climate_index_importer.requests.get",
            return_value=ChartResponse(png_bytes()),
        ) as get:
            first = sync_chart(1)
            second = sync_chart(1)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.scope, "central-africa")
        self.assertTrue(storages["rcc_data"].exists(second.object_name))
        get.assert_called_with(
            f"{SOURCE_ROOT}/hs_hg1.png",
            stream=True,
            timeout=(15, 90),
            allow_redirects=False,
        )
        with self.assertRaisesMessage(ValueError, "between 1 and 22"):
            chart_details(23)
        with patch(
            "climweb.pages.services.climate_index_importer.requests.get",
            return_value=ChartResponse(b"not a png"),
        ):
            with self.assertRaisesMessage(ValueError, "not a PNG"):
                sync_chart(2)

    def test_gallery_filters_and_serves_only_local_images(self):
        central = self.make_asset(1, "central-africa", "Central Africa rainfall trends")
        africa = self.make_asset(14, "africa", "Africa temperature trends")
        gallery_url = reverse("rcc_climate_index_gallery")

        response = self.client.get(gallery_url)
        self.assertContains(response, central.title)
        self.assertContains(response, africa.title)
        self.assertNotContains(response, "rcc.acmad.org/graphmap")
        filtered = self.client.get(gallery_url, {"scope": "africa"})
        self.assertContains(filtered, africa.title)
        self.assertNotContains(filtered, central.title)

        image_url = reverse("rcc_climate_index_file", args=[central.pk])
        image = self.client.get(image_url)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/png")
        self.assertEqual(b"".join(image.streaming_content), png_bytes())
        download = self.client.get(image_url, {"download": "1"})
        self.assertIn("attachment", download["Content-Disposition"])
