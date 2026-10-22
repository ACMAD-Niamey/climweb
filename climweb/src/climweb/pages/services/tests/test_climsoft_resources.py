import io
import tempfile
import zipfile
from io import StringIO
from unittest.mock import Mock, patch

from django.core.files.storage import storages
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.documents import get_document_model

from climweb.pages.services.management.commands.import_rcc_climsoft_resources import validate_document


def pptx_bytes():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/presentation.xml", "<presentation/>")
    return output.getvalue()


class ClimsoftResourceTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_override = override_settings(MEDIA_ROOT=self.temp_dir.name)
        self.storage_override.enable()
        storages._storages.clear()

    def tearDown(self):
        storages._storages.clear()
        self.storage_override.disable()
        self.temp_dir.cleanup()

    @patch("climweb.pages.services.management.commands.import_rcc_climsoft_resources.requests.get")
    def test_imports_once_and_renders_local_resources(self, get):
        def response_for(url, **kwargs):
            content = pptx_bytes() if url.endswith(".pptx") else b"%PDF-1.4\nClimsoft test resource"
            response = Mock(content=content, status_code=200)
            response.raise_for_status.return_value = None
            return response

        get.side_effect = response_for
        call_command("import_rcc_climsoft_resources", stdout=StringIO())
        call_command("import_rcc_climsoft_resources", stdout=StringIO())

        Document = get_document_model()
        self.assertEqual(Document.objects.filter(tags__name="Climsoft").count(), 7)
        self.assertEqual(get.call_count, 7)
        response = self.client.get(reverse("rcc_climsoft_resources"))
        self.assertContains(response, "Climsoft Administrator Guide")
        self.assertContains(response, "RClimDex User Manual")
        self.assertNotContains(response, "rcc.acmad.org/manuelclimsoft")
        filtered = self.client.get(reverse("rcc_climsoft_resources"), {"category": "data-entry"})
        self.assertContains(filtered, "Climsoft Key Entry Guide")
        self.assertNotContains(filtered, "Climsoft Programmer Guide")

    def test_rejects_invalid_document_content(self):
        with self.assertRaisesMessage(ValueError, "did not return a PDF"):
            validate_document(b"not a pdf", "manual.pdf")
        with self.assertRaisesMessage(ValueError, "valid PowerPoint"):
            validate_document(b"not a pptx", "slides.pptx")
