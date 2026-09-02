from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import CustomDocumentModel
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.services.models import ServiceIndexPage, ServicePage


class TestSeedCuipServiceCommand(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        cls.service_index = ServiceIndexPage.objects.first()
        if not cls.service_index:
            cls.service_index = ServiceIndexPage(title="Services", slug="services")
            home.add_child(instance=cls.service_index)
            cls.service_index.save_revision().publish()

    def test_command_creates_editable_four_sector_page(self):
        call_command("seed_cuip_service", stdout=StringIO())

        page = ServicePage.objects.get(slug="cuip")
        self.assertTrue(page.live)
        self.assertEqual(len(page.service_sectors), 4)
        self.assertEqual(
            [block.value["anchor"] for block in page.service_sectors],
            ["agriculture", "health", "water", "disaster-risk-reduction"],
        )
        health = page.service_sectors[1].value
        self.assertEqual(
            health["external_tools"][0]["url"],
            "https://openmap.clarity.io/",
        )
        self.assertEqual(len(health["tor_documents"]), 1)
        self.assertIn("Secretariat provided by ACMAD", str(health["rules_of_procedure"]))
        agriculture = page.service_sectors[0].value
        self.assertEqual(len(agriculture["tor_documents"]), 2)
        self.assertIn("ConceptNoteUserInterfaceWorkshop.pdf", agriculture["tor_documents"][0]["url"])
        self.assertIn("TDR_Task-Force-AA_SECAL", agriculture["meetings"][0]["url"])
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="sector-panel"', count=4)
        self.assertContains(response, "Air Quality Monitoring Map")
        self.assertContains(response, "Terms of Reference", count=4)
        self.assertContains(response, "TOR documents and adoption records", count=4)

    def test_command_preserves_existing_dashboard_content(self):
        call_command("seed_cuip_service", stdout=StringIO())
        page = ServicePage.objects.get(slug="cuip")
        page.sector_heading = "Editor supplied heading"
        page.save_revision().publish()

        call_command("seed_cuip_service", stdout=StringIO())
        page.refresh_from_db()

        self.assertEqual(page.sector_heading, "Editor supplied heading")
        self.assertEqual(len(page.service_sectors), 4)

    @patch("climweb.pages.services.management.commands.seed_cuip_service.requests.get")
    def test_downloads_documents_once_and_replaces_external_links(self, mock_get):
        response = Mock(content=b"%PDF-1.4\nCUIP test document")
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        call_command("seed_cuip_service", stdout=StringIO())
        page = ServicePage.objects.get(slug="cuip")
        agriculture = page.service_sectors[0].value
        self.assertTrue(agriculture["tor_documents"][0]["url"].startswith("https://"))

        call_command("seed_cuip_service", "--download-documents", stdout=StringIO())

        page.refresh_from_db()
        agriculture = page.service_sectors[0].value
        self.assertEqual(CustomDocumentModel.objects.filter(tags__name="CUIP").count(), 3)
        self.assertTrue(agriculture["tor_documents"][0]["url"].startswith("/documents/"))
        self.assertTrue(agriculture["meetings"][0]["url"].startswith("/documents/"))

        call_command("seed_cuip_service", "--download-documents", stdout=StringIO())

        self.assertEqual(CustomDocumentModel.objects.filter(tags__name="CUIP").count(), 3)
        self.assertEqual(mock_get.call_count, 3)
