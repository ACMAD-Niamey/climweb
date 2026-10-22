from io import StringIO

from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.flex_page.models import FlexPage
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.services.models import MeteorologicalService


class TestSeedMetServicesCommand(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = get_or_create_homepage()

    def test_create_page_seeds_directory_and_page_block(self):
        call_command("seed_met_services", "--create-page", stdout=StringIO())

        page = FlexPage.objects.get(title="Met Services")

        self.assertTrue(page.live)
        self.assertEqual(page.get_parent().specific, self.home_page)
        self.assertTrue(
            any(block.block_type == "met_services_directory" for block in page.content)
        )
        self.assertEqual(MeteorologicalService.objects.count(), 53)

    def test_existing_empty_flex_page_gets_directory_block(self):
        page = FlexPage(
            title="Met Services",
            slug="met-services",
            banner_title="Met Services",
            content=[],
        )
        self.home_page.add_child(instance=page)
        page.save_revision().publish()

        call_command("seed_met_services", "--create-page", stdout=StringIO())
        page.refresh_from_db()

        self.assertTrue(
            any(block.block_type == "met_services_directory" for block in page.content)
        )
