from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.models import ElNinoPage
from .factories import ProductIndexPageFactory


class SeedElNinoPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        ProductIndexPageFactory(parent=home)
        ServiceCategory.objects.create(name="Seasonal and Long-Range Forecasts", icon="chart-line")

    def test_command_creates_page_and_is_idempotent(self):
        call_command("seed_el_nino_page")
        call_command("seed_el_nino_page")

        page = ElNinoPage.objects.get(slug="el-nino-africa")
        self.assertTrue(page.live)
        self.assertEqual(ElNinoPage.objects.count(), 1)
        self.assertEqual(page.product.temporal_resolution, "monthly")
        self.assertEqual(page.product.product_item_types[0][1], "Monthly Bulletin - El Niño Bulletin")
