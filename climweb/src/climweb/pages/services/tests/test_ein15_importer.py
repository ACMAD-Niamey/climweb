import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from django.urls import reverse
from django_celery_beat.models import PeriodicTask

from climweb.pages.services.ein15_importer import (
    CATALOGUE_URL, discover_files, source_url_for, sync_file, validate_catalogue_url,
)
from climweb.pages.services.models import RCCEIN15Asset, RCCEIN15ImportConfig, RCCEIN15ImportRun
from climweb.pages.services.tasks import create_rcc_ein15_run, execute_rcc_ein15_import


FILE = "WAfr50_STS.1998010100.nc"
OTHER = "WAfr50_SRF.1998020100.nc"
NETCDF = b"CDF\x01" + b"\x00" * 48


class SourceResponse:
    status_code = 200

    def __init__(self, body, headers=None):
        self.body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.body


class EIN15ImporterTests(TestCase):
    def test_discovery_only_accepts_expected_netcdf_paths(self):
        xml = b'''<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
            <dataset urlPath="ein15output/WAfr50_STS.1998010100.nc">
                <dataSize units="Mbytes">2.908</dataSize><date type="modified">2015-04-15T17:24:10Z</date>
            </dataset>
            <dataset urlPath="ein15output/../../bad.nc" />
            <dataset urlPath="cordex/WAfr50_STS.1998010100.nc" />
        </catalog>'''
        with patch("climweb.pages.services.ein15_importer.requests.get", return_value=SourceResponse(xml)) as get:
            self.assertEqual(discover_files(), [{
                "filename": FILE, "size": "2.908 Mbytes", "modified": "2015-04-15T17:24:10Z",
            }])
        get.assert_called_once_with(CATALOGUE_URL, stream=True, timeout=(15, 45), allow_redirects=False)
        with self.assertRaises(ValidationError):
            validate_catalogue_url(CATALOGUE_URL.replace("sgbd.acmad.org", "127.0.0.1"))
        with self.assertRaises(ValidationError):
            source_url_for(CATALOGUE_URL, "../evil.nc")

    def test_streaming_stores_a_valid_netcdf_and_serves_admin_download(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "rcc_data": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": directory}},
            }):
                storages._storages.clear()
                try:
                    response = SourceResponse(NETCDF, {"Content-Length": str(len(NETCDF)), "Last-Modified": "Wed, 15 Apr 2015 17:24:10 GMT"})
                    with patch("climweb.pages.services.ein15_importer.requests.get", return_value=response):
                        asset = sync_file(CATALOGUE_URL, FILE)
                    self.assertEqual(asset.size_bytes, len(NETCDF))
                    self.assertTrue(storages["rcc_data"].exists(asset.object_name))
                    self.assertEqual(self.client.get(reverse("rcc_ein15_download", args=[asset.pk])).status_code, 302)
                    user = get_user_model().objects.create_superuser("ein15-admin", "ein15@example.test", "password")
                    self.client.force_login(user)
                    download = self.client.get(reverse("rcc_ein15_download", args=[asset.pk]))
                    self.assertEqual(download.status_code, 200)
                    self.assertEqual(b"".join(download.streaming_content), NETCDF)
                    not_modified = SourceResponse(b"")
                    not_modified.status_code = 304
                    with patch("climweb.pages.services.ein15_importer.requests.get", return_value=not_modified) as get:
                        self.assertEqual(sync_file(CATALOGUE_URL, FILE).pk, asset.pk)
                    self.assertEqual(get.call_args.kwargs["headers"], {"If-Modified-Since": response.headers["Last-Modified"]})
                    with patch("climweb.pages.services.ein15_importer.requests.get", return_value=SourceResponse(b"bad")):
                        with self.assertRaisesMessage(ValueError, "not a NetCDF"):
                            sync_file(CATALOGUE_URL, OTHER)
                    self.assertEqual(RCCEIN15Asset.objects.count(), 1)
                finally:
                    storages._storages.clear()

    def test_rejects_oversized_download_before_streaming(self):
        response = SourceResponse(NETCDF, {"Content-Length": str(4 * 1024 ** 3)})
        with patch("climweb.pages.services.ein15_importer.requests.get", return_value=response):
            with self.assertRaisesMessage(ValueError, "size limit"):
                sync_file(CATALOGUE_URL, FILE)

    def test_dashboard_discovery_selection_and_manual_queue(self):
        user = get_user_model().objects.create_superuser("ein15-dashboard", "dashboard@example.test", "password")
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("rcc_imports")), "EIN15 regional model output")
        self.assertEqual(self.client.get(reverse("rcc_ein15_imports")).status_code, 200)
        config = RCCEIN15ImportConfig.objects.get()
        self.assertFalse(config.enabled)
        with patch("climweb.pages.services.ein15_admin.discover_files", return_value=[{"filename": FILE, "size": "2.9 Mbytes", "modified": "2015"}]):
            self.client.post(reverse("rcc_ein15_imports"), {"action": "discover"})
        self.client.post(reverse("rcc_ein15_imports"), {"action": "save_files", "files": [FILE]})
        config.refresh_from_db()
        self.assertEqual(config.selected_files, [FILE])
        self.assertFalse(PeriodicTask.objects.get(name="rcc-ein15-import").enabled)
        with patch("climweb.pages.services.ein15_admin.execute_rcc_ein15_import.delay") as queue:
            self.client.post(reverse("rcc_ein15_imports"), {"action": "run"})
        self.assertEqual(RCCEIN15ImportRun.objects.get().files, [FILE])
        queue.assert_called_once()

    def test_run_reports_partial_failures_and_guards_concurrent_runs(self):
        config = RCCEIN15ImportConfig.objects.create(
            discovered_files=[{"filename": FILE}, {"filename": OTHER}], selected_files=[FILE, OTHER],
        )
        run = create_rcc_ein15_run(config.pk, "manual")
        self.assertIsNone(create_rcc_ein15_run(config.pk, "manual"))
        with patch("climweb.pages.services.tasks.sync_ein15_file", side_effect=[Mock(), ValueError("source unavailable")]):
            execute_rcc_ein15_import(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "partial")
        self.assertEqual([item["status"] for item in run.results], ["succeeded", "failed"])
