import hashlib
import tempfile

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from climweb.pages.services.models import RCCEIN15Asset


NETCDF = b"CDF\x01" + b"\x00" * 24


class EIN15ArchiveTests(TestCase):
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

    def make_asset(self, filename, store=True):
        object_name = f"ein15/{filename}/test.nc"
        if store:
            storages["rcc_data"].save(object_name, ContentFile(NETCDF))
        return RCCEIN15Asset.objects.create(
            filename=filename,
            source_url=f"http://sgbd.acmad.org:8080/thredds/fileServer/ein15output/{filename}",
            object_name=object_name,
            checksum_sha256=hashlib.sha256(NETCDF).hexdigest(),
            size_bytes=len(NETCDF),
            synced_at=timezone.now(),
        )

    def test_archive_lists_locally_hosted_files_and_filters_groups(self):
        url = reverse("rcc_ein15_archive")
        self.assertContains(self.client.get(url), "Files are being prepared")
        sts = self.make_asset("WAfr50_STS.1998010100.nc")
        self.make_asset("WAfr50_ATM.1998020100.nc")

        response = self.client.get(url)
        self.assertContains(response, sts.filename)
        self.assertContains(response, "WAfr50_ATM.1998020100.nc")
        self.assertContains(response, "01 Jan 1998")
        self.assertContains(response, reverse("rcc_ein15_file", args=[sts.pk]))
        self.assertNotContains(response, "sgbd.acmad.org")

        filtered = self.client.get(url, {"type": "STS"})
        self.assertContains(filtered, sts.filename)
        self.assertNotContains(filtered, "WAfr50_ATM.1998020100.nc")
        self.assertContains(self.client.get(url, {"type": "RAD"}), "No files match this group")

    def test_public_download_uses_local_storage_only(self):
        asset = self.make_asset("WAfr50_STS.1998010100.nc")
        url = reverse("rcc_ein15_file", args=[asset.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/x-netcdf")
        self.assertIn(asset.filename, response["Content-Disposition"])
        self.assertEqual(response["X-Checksum-SHA256"], asset.checksum_sha256)
        self.assertEqual(b"".join(response.streaming_content), NETCDF)
        self.assertEqual(self.client.get(reverse("rcc_ein15_file", args=[9999])).status_code, 404)

    def test_missing_local_file_returns_404(self):
        asset = self.make_asset("WAfr50_STS.1998010100.nc", store=False)
        self.assertEqual(self.client.get(reverse("rcc_ein15_file", args=[asset.pk])).status_code, 404)
