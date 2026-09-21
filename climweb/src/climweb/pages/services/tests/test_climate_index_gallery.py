import hashlib
import io
import tempfile
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from climweb.pages.services.climate_index_importer import SOURCE_ROOT, chart_details, sync_chart, validate_source_url
from climweb.pages.services.models import (
    RCCClimateIndexAsset, RCCClimateIndexImportConfig, RCCClimateIndexImportRun,
    RCCClimateIndexVersion,
)
from climweb.pages.services.tasks import create_rcc_climate_index_run, execute_rcc_climate_index_import


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

    def test_dashboard_adds_future_graph_without_code_change(self):
        user = get_user_model().objects.create_superuser("index-admin", "index@example.test", "pass")
        self.client.force_login(user)
        response = self.client.post(reverse("rcc_climate_index_imports"), {
            "action": "save_asset",
            "legacy_index": 23,
            "title": "New rainfall index",
            "scope": "africa",
            "period": "2021–2025",
            "description": "A newly published graph.",
            "source_url": f"{SOURCE_ROOT}/new-index.png",
            "active": "on",
        })
        self.assertEqual(response.status_code, 302)
        asset = RCCClimateIndexAsset.objects.get(legacy_index=23)
        self.assertEqual(asset.title, "New rainfall index")
        self.assertTrue(asset.active)
        dashboard = self.client.get(reverse("rcc_climate_index_imports"))
        self.assertContains(dashboard, "New rainfall index")
        self.assertContains(self.client.get(reverse("rcc_imports")), "Climate indices and historical graphs")

    def test_managed_run_records_versions_and_errors(self):
        asset = RCCClimateIndexAsset.objects.create(
            legacy_index=23, title="New graph", scope="other",
            source_url=f"{SOURCE_ROOT}/new-graph.png",
        )
        config = RCCClimateIndexImportConfig.objects.create()
        run = create_rcc_climate_index_run(config.pk, "manual", asset_ids=[asset.pk])
        with patch(
            "climweb.pages.services.climate_index_importer.requests.get",
            return_value=ChartResponse(png_bytes()),
        ):
            execute_rcc_climate_index_import(run.pk)
        run.refresh_from_db()
        asset.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(RCCClimateIndexVersion.objects.filter(asset=asset).count(), 1)
        self.assertEqual(asset.last_error, "")

        failed_run = RCCClimateIndexImportRun.objects.create(
            config=config, trigger="manual", asset_ids=[asset.pk],
        )
        with patch(
            "climweb.pages.services.climate_index_importer.requests.get",
            return_value=ChartResponse(b"invalid"),
        ):
            execute_rcc_climate_index_import(failed_run.pk)
        failed_run.refresh_from_db()
        asset.refresh_from_db()
        self.assertEqual(failed_run.status, "failed")
        self.assertIn("not a PNG", asset.last_error)
        self.assertEqual(RCCClimateIndexVersion.objects.filter(asset=asset).count(), 1)

    def test_source_urls_are_restricted_to_approved_https_png_hosts(self):
        with self.assertRaises(ValidationError):
            validate_source_url("http://127.0.0.1/private.png")
        with self.assertRaises(ValidationError):
            validate_source_url("https://rcc.acmad.org/not-an-image.pdf")
