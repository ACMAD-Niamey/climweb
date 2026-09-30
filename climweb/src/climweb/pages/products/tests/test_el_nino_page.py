from datetime import date

from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import ElNinoPageFactory, ProductIndexPageFactory, ProductItemPageFactory


class ElNinoPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        product_index = ProductIndexPageFactory(parent=home)
        cls.page = ElNinoPageFactory(parent=product_index)

    def test_page_explains_african_context_and_acmad_action(self):
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El Niño in Africa")
        self.assertContains(response, "What ACMAD is doing")
        self.assertContains(response, "How ACMAD supports the continent")
        self.assertNotContains(response, "Read the latest bulletin")
        self.assertContains(response, 'class="enso-intro-copy"')
        self.assertContains(response, 'class="enso-intro-bulletin"')
        self.assertContains(response, "Latest Elnino Bulletin")
        self.assertNotContains(response, "Updated monthly")
        self.assertNotContains(response, "The monthly bulletin brings together")
        self.assertContains(response, "Previous El Niño bulletins")
        self.assertContains(response, "No previous editions yet")

    def test_settings_expose_page_visibility_control(self):
        form = type(self.page).get_edit_handler().get_form_class()

        self.assertIn("is_visible", form.base_fields)

    def test_hidden_page_and_its_bulletins_are_not_public(self):
        bulletin = ProductItemPageFactory(parent=self.page)
        self.page.is_visible = False
        self.page.save_revision().publish()

        self.assertEqual(self.client.get(self.page.url).status_code, 404)
        self.assertEqual(self.client.get(bulletin.url).status_code, 404)

    def test_latest_monthly_bulletin_is_featured(self):
        older = ProductItemPageFactory(parent=self.page, title="El Niño Bulletin — July 2026")
        latest = ProductItemPageFactory(
            parent=self.page,
            title="El Niño Bulletin — August 2026",
            products__0__document_product__product_type="Monthly El Niño Bulletin",
            products__0__document_product__date=date(2026, 8, 1),
        )
        type(older).objects.filter(pk=older.pk).update(date=date(2026, 7, 1))
        type(latest).objects.filter(pk=latest.pk).update(date=date(2026, 8, 1))

        response = self.client.get(self.page.url)

        self.assertNotContains(response, "Latest issue")
        self.assertNotContains(response, latest.title)
        self.assertNotContains(response, "August 2026")
        document_url = next(
            block.value.get("document").url
            for block in latest.products
            if block.block_type == "document_product"
        )
        self.assertContains(
            response,
            f'class="button is-primary" href="{document_url}"',
        )
        self.assertContains(response, older.title)
        self.assertContains(response, "Previous El Niño bulletins")
