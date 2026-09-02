from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.tests.factories import (
    ProductIndexPageFactory,
    ProductPageFactory,
)


class TestProductListingIcons(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        cls.index = ProductIndexPageFactory(parent=home)
        invalid_icon_service = ServiceCategory.objects.create(
            name="Service with unsupported icon",
            icon="icon-that-does-not-exist",
        )
        ProductPageFactory(parent=cls.index, service=invalid_icon_service)

    def test_unsupported_service_icon_uses_globe_fallback(self):
        response = self.client.get(self.index.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">None<")
        self.assertContains(response, 'id="icon-globe"')
