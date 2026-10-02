from datetime import date, timedelta

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
        self.assertContains(response, "During El Niño")
        self.assertContains(response, "does not produce the same outcome everywhere")
        self.assertContains(response, "How ACMAD supports the continent")
        self.assertNotContains(response, "A continental perspective")
        self.assertNotContains(response, "Read the latest bulletin")
        self.assertContains(response, 'class="enso-intro-copy"')
        self.assertContains(response, 'class="enso-hero-bulletin"')
        self.assertContains(response, 'class="enso-explainer"')
        self.assertContains(response, 'class="enso-explanation"')
        self.assertNotContains(response, 'class="enso-context-card')
        self.assertNotContains(response, "What ACMAD is doing")
        self.assertNotContains(response, 'class="enso-intro-bulletin"')
        self.assertLess(
            response.content.index(b'class="enso-explainer"'),
            response.content.index(b'class="enso-intro-copy"'),
        )
        self.assertContains(response, "Latest ENSO Bulletin")
        self.assertNotContains(response, "Updated monthly")
        self.assertNotContains(response, "The monthly bulletin brings together")
        self.assertContains(response, "Previous ENSO bulletins")
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
            f'class="button is-primary enso-hero-bulletin__button" href="{document_url}"',
        )
        self.assertNotContains(response, "Download PDF")
        self.assertContains(response, older.title)
        self.assertContains(response, "Previous ENSO bulletins")

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

        self.assertContains(response, "ENSO related activities")
        self.assertContains(response, related.title)
        self.assertContains(response, related_news.title)
        self.assertNotContains(response, related.listing_summary)
        self.assertNotContains(response, related_news.listing_summary)
        self.assertLess(
            response.content.index(b'id="el-nino-updates-heading"'),
            response.content.index(b'id="acmad-action-heading"'),
        )
        self.assertNotContains(response, unrelated.title)
        self.assertNotContains(response, hidden.title)
        self.assertNotContains(response, unrelated_news.title)

    def test_event_editor_exposes_el_nino_related_option(self):
        from climweb.pages.events.models import EventPage

        form = EventPage.get_edit_handler().get_form_class()

        self.assertIn("is_el_nino_related", form.base_fields)
        self.assertIn("enso_host_organisation", form.base_fields)
        self.assertIn("enso_external_url", form.base_fields)

    def test_partner_news_and_events_link_to_the_external_host(self):
        events_index = EventIndexPageFactory(parent=self.home)
        partner_event = EventPageFactory(
            parent=events_index,
            title="PAFO ENSO preparedness workshop",
            is_el_nino_related=True,
            enso_host_organisation="PAFO",
            enso_external_url="https://pafo-africa.org/enso-workshop/",
        )
        news_index = NewsIndexPageFactory(parent=self.home)
        partner_news = NewsPageFactory(
            parent=news_index,
            title="ICPAC regional ENSO briefing",
            date=timezone.now(),
            is_el_nino_related=True,
            enso_host_organisation="ICPAC",
            enso_external_url="https://www.icpac.net/enso-briefing/",
        )

        response = self.client.get(self.page.url)

        self.assertContains(response, "Partner activity", count=2)
        self.assertContains(response, "Hosted by", count=2)
        self.assertContains(response, "<strong>PAFO</strong>", html=True)
        self.assertContains(response, "<strong>ICPAC</strong>", html=True)
        self.assertContains(response, "In collaboration with ACMAD", count=2)
        self.assertContains(response, "View on PAFO")
        self.assertContains(response, "View on ICPAC")
        self.assertContains(response, 'href="https://pafo-africa.org/enso-workshop/" target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, 'href="https://www.icpac.net/enso-briefing/" target="_blank" rel="noopener noreferrer"')
        self.assertNotContains(response, f'href="{partner_event.url}"')
        self.assertNotContains(response, f'href="{partner_news.url}"')

    def test_related_updates_are_paginated_three_per_page(self):
        news_index = NewsIndexPageFactory(parent=self.home)
        news_items = [
            NewsPageFactory(
                parent=news_index,
                title=f"El Niño update {number}",
                date=timezone.now() - timedelta(days=number),
                is_el_nino_related=True,
            )
            for number in range(4)
        ]

        first_page = self.client.get(self.page.url)
        second_page = self.client.get(self.page.url, {"updates_page": 2})

        for item in news_items[:3]:
            self.assertContains(first_page, item.title)
        self.assertNotContains(first_page, news_items[3].title)
        self.assertContains(first_page, "Page 1 of 2")
        self.assertContains(first_page, "updates_page=2")
        self.assertContains(second_page, news_items[3].title)
        self.assertContains(second_page, "Page 2 of 2")

    def test_news_editor_exposes_el_nino_related_option(self):
        from climweb.pages.news.models import NewsPage

        form = NewsPage.get_edit_handler().get_form_class()

        self.assertIn("is_el_nino_related", form.base_fields)
        self.assertIn("enso_host_organisation", form.base_fields)
        self.assertIn("enso_external_url", form.base_fields)

    def test_el_nino_editor_exposes_explainer_image(self):
        form = type(self.page).get_edit_handler().get_form_class()

        self.assertIn("explainer_image", form.base_fields)
