from io import StringIO

from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.flex_page.models import FlexPage
from climweb.pages.home.models import RegionalClimateCentre, RegionalClimateCentreMapNode
from climweb.pages.home.tests.factories import get_or_create_homepage


class TestSeedRCCDirectoryCommand(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = get_or_create_homepage()
        cls.centre = RegionalClimateCentre.objects.create(
            display_name="Test RCC",
            full_name="Test Regional Climate Centre",
            city="Niamey",
            country="Niger",
            website_url="https://rcc.example.test/",
            map_x="68.3",
            map_y="92.6",
        )
        cls.network = RegionalClimateCentre.objects.create(
            display_name="Test RCC-Network",
            full_name="Test Regional Climate Centre Network",
            centre_type=RegionalClimateCentre.TYPE_NETWORK,
            coverage="Test region",
            website_url="https://network.example.test/",
            status=RegionalClimateCentre.STATUS_INITIATED,
            map_x="210.0",
            map_y="160.0",
        )
        RegionalClimateCentreMapNode.objects.create(
            centre=cls.network,
            name="Test node",
            map_x="220.0",
            map_y="180.0",
        )

    def test_create_page_uses_existing_rcc_snippets(self):
        call_command("seed_rcc_directory", "--create-page", stdout=StringIO())

        page = FlexPage.objects.get(title="Regional Climate Centres")
        self.assertTrue(page.live)
        self.assertEqual(page.get_parent().specific, self.home_page)
        self.assertTrue(any(block.block_type == "rcc_directory" for block in page.content))

        response = self.client.get(page.url)
        self.assertContains(response, "Test Regional Climate Centre")
        self.assertContains(response, "Niamey, Niger")
        self.assertContains(response, "WMO designated")
        self.assertContains(response, "https://rcc.example.test/")
        self.assertContains(response, "Test Regional Climate Centre Network")
        self.assertContains(response, "RCC Network · Initiated")
        self.assertContains(response, 'class="rcc-network-node rcc-marker--initiated"')
        self.assertContains(response, "Initiated RCC Network")

        homepage_response = self.client.get(self.home_page.url)
        self.assertContains(homepage_response, page.url)

    def test_existing_empty_flex_page_gets_directory_block(self):
        page = FlexPage(
            title="Regional Climate Centres",
            slug="regional-climate-centres",
            banner_title="Regional Climate Centres",
            content=[],
        )
        self.home_page.add_child(instance=page)
        page.save_revision().publish()

        call_command("seed_rcc_directory", "--create-page", stdout=StringIO())
        page.refresh_from_db()

        self.assertTrue(any(block.block_type == "rcc_directory" for block in page.content))
