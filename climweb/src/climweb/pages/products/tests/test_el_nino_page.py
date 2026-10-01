from datetime import date

from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.events.tests.factories import EventIndexPageFactory, EventPageFactory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.news.tests.factories import NewsIndexPageFactory, NewsPageFactory
from .factories import ElNinoPageFactory, ProductIndexPageFactory, ProductItemPageFactory


class ElNinoPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = get_or_create_homepage()
        product_index = ProductIndexPageFactory(parent=cls.home)
        cls.page = ElNinoPageFactory(parent=product_index)

    def test_page_explains_african_context_and_acmad_action(self):
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El Niño in Africa")
        self.assertContains(response, "What ACMAD is doing")
        self.assertContains(response, "How ACMAD supports the continent")
        self.assertNotContains(response, "A continental perspective")
        self.assertNotContains(response, "Read the latest bulletin")
        self.assertContains(response, 'class="enso-intro-copy"')
        self.assertContains(response, 'class="enso-hero-bulletin"')
        self.assertContains(response, 'class="enso-explainer"')
        self.assertNotContains(response, 'class="enso-intro-bulletin"')
        self.assertLess(
            response.content.index(b'class="enso-explainer"'),
            response.content.index(b'class="enso-intro-copy"'),
        )
        self.assertContains(response, "Latest Elnino Bulletin")
        self.assertNotContains(response, "Updated monthly")
        self.assertNotContains(response, "The monthly bulletin brings together")
        self.assertContains(response, "Previous El Niño bulletins")
        self.assertContains(response, "No previous editions yet")

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

    def test_only_related_published_news_and_events_appear(self):
        events_index = EventIndexPageFactory(parent=self.home)
        related = EventPageFactory(
            parent=events_index,
            title="Africa El Niño Preparedness Forum",
            is_el_nino_related=True,
        )
        unrelated = EventPageFactory(
            parent=events_index,
            title="General Climate Forum",
            is_el_nino_related=False,
        )
        hidden = EventPageFactory(
            parent=events_index,
            title="Hidden El Niño Forum",
            is_el_nino_related=True,
            is_hidden=True,
        )
        news_index = NewsIndexPageFactory(parent=self.home)
        related_news = NewsPageFactory(
            parent=news_index,
            title="ACMAD publishes new El Niño analysis",
            date=timezone.now(),
            is_el_nino_related=True,
        )
        unrelated_news = NewsPageFactory(
            parent=news_index,
            title="General ACMAD update",
            date=timezone.now(),
            is_el_nino_related=False,
        )

        response = self.client.get(self.page.url)

        self.assertContains(response, "El Niño news and events")
        self.assertContains(response, related.title)
        self.assertContains(response, related_news.title)
        self.assertNotContains(response, related.listing_summary)
        self.assertNotContains(response, related_news.listing_summary)
        self.assertNotContains(response, unrelated.title)
        self.assertNotContains(response, hidden.title)
        self.assertNotContains(response, unrelated_news.title)

    def test_event_editor_exposes_el_nino_related_option(self):
        from climweb.pages.events.models import EventPage

        form = EventPage.get_edit_handler().get_form_class()

        self.assertIn("is_el_nino_related", form.base_fields)

    def test_news_editor_exposes_el_nino_related_option(self):
        from climweb.pages.news.models import NewsPage

        form = NewsPage.get_edit_handler().get_form_class()

        self.assertIn("is_el_nino_related", form.base_fields)

    def test_el_nino_editor_exposes_explainer_image(self):
        form = type(self.page).get_edit_handler().get_form_class()

        self.assertIn("explainer_image", form.base_fields)
