from datetime import timedelta
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import override_settings
from django.utils import timezone
from wagtail.models import PageViewRestriction
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.events.tests.factories import EventIndexPageFactory, EventPageFactory
from climweb.pages.news.tests.factories import NewsIndexPageFactory, NewsPageFactory
from climweb.pages.products.tests.factories import (
    ElNinoPageFactory,
    ProductIndexPageFactory,
    ProductItemPageFactory,
    ProductPageFactory,
)
from climweb.pages.summer_school.tests.factories import (
    SummerSchoolIndexPageFactory,
    SummerSchoolPageFactory,
)
from .factories import get_or_create_homepage


class HeroUpdatesTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = get_or_create_homepage()
        cls.news_index = NewsIndexPageFactory(parent=cls.home)
        cls.events_index = EventIndexPageFactory(parent=cls.home)

    def news(self, days=0, **kwargs):
        return NewsPageFactory(parent=self.news_index, date=timezone.now() + timedelta(days=days), **kwargs)

    def event(self, days=1, **kwargs):
        return EventPageFactory(parent=self.events_index, date_from=timezone.now() + timedelta(days=days), **kwargs)

    def ids(self):
        return [slide["id"] for slide in self.home.get_hero_updates()]

    def manual(self, *pages):
        self.home.hero_updates_mode = "manual"
        self.home.hero_featured_updates = [
            ("news" if hasattr(page, "date") else "event", page) for page in pages
        ]

    def test_automatic_uses_only_the_newest_news_as_the_lead_slide(self):
        self.event(20)
        self.event(2)
        older = self.news(-2)
        newest = self.news(-1)
        self.news(-5)
        self.assertEqual(self.ids(), [newest.pk])

    def test_excludes_past_events_and_future_dated_news(self):
        self.event(-2)
        self.event(-5, date_to=timezone.now() - timedelta(days=1))
        self.news(1)
        self.assertEqual(self.ids(), [])

    def test_automatic_does_not_use_events(self):
        self.event(-1, date_to=timezone.now() + timedelta(days=1))
        self.event(2)
        self.assertEqual(self.ids(), [])

    def test_manual_mode_can_still_use_an_event_as_the_lead(self):
        event = EventPageFactory(parent=self.events_index, date_from=timezone.now().replace(hour=0, minute=0))
        self.manual(event)
        self.assertEqual(self.ids(), [event.pk])

    def test_news_only_uses_the_newest_item(self):
        news = [self.news(-days) for days in range(1, 5)]
        self.assertEqual(self.ids(), [news[0].pk])

    def test_events_only_do_not_create_an_automatic_lead(self):
        for days in range(1, 5):
            self.event(days)
        self.assertEqual(self.ids(), [])

    def test_manual_configuration_survives_publishing(self):
        news = self.news(-1)
        event = self.event(1)
        self.manual(news, event)
        self.home.save_revision().publish()
        self.home.refresh_from_db()
        self.assertEqual(self.home.hero_updates_mode, "manual")
        self.assertEqual(self.ids(), [news.pk])

    def test_dashboard_panel_exposes_only_new_hero_fields_and_limits_selection(self):
        from wagtail.blocks import StreamBlockValidationError
        form = type(self.home).get_edit_handler().get_form_class()
        self.assertIn("hero_updates_mode", form.base_fields)
        self.assertIn("hero_featured_updates", form.base_fields)
        self.assertIn("hero_featured_products", form.base_fields)
        self.manual(*(self.news(-day) for day in range(1, 5)))
        with self.assertRaises(StreamBlockValidationError):
            self.home.hero_featured_updates.stream_block.clean(self.home.hero_featured_updates)

    def test_excludes_drafts_and_inherited_private_pages(self):
        self.news(-1, live=False)
        self.event(1, live=False)
        self.news(-2)
        self.event(2)
        PageViewRestriction.objects.create(page=self.news_index, restriction_type="login")
        PageViewRestriction.objects.create(page=self.events_index, restriction_type="login")
        self.assertEqual(self.ids(), [])

    def test_manual_preserves_order_and_deduplicates(self):
        older = self.news(-2)
        newest = self.news(-1)
        self.manual(older, newest, older)
        self.assertEqual(self.ids(), [older.pk])

    def test_manual_skips_unpublished_or_private_selected_pages(self):
        news = self.news(-1)
        event = self.event(1)
        self.manual(news, event)
        type(news).objects.filter(pk=news.pk).update(live=False)
        PageViewRestriction.objects.create(page=self.events_index, restriction_type="login")
        self.assertEqual(self.ids(), [])

    def test_manual_empty_does_not_fall_back_to_automatic(self):
        self.news(-1)
        self.manual()
        self.assertEqual(self.ids(), [])

    def test_manual_refetches_latest_saved_title(self):
        news = self.news(-1)
        self.manual(news)
        type(news).objects.filter(pk=news.pk).update(title="Updated title")
        self.assertEqual(self.home.get_hero_updates()[0]["title"], "Updated title")

    def test_other_homepage_content_is_excluded(self):
        from .factories import HomePageFactory
        other_home = HomePageFactory()
        other_index = NewsIndexPageFactory(parent=other_home)
        other_news = NewsPageFactory(parent=other_index, date=timezone.now() - timedelta(days=1))
        self.manual(other_news)
        self.assertEqual(self.ids(), [])

    def test_single_slide_has_fallback_and_no_controls(self):
        news = self.news(-1)
        with patch.object(type(news), "get_meta_image", return_value=None):
            html = render_to_string("home/section/hero_updates_widget.html", {"hero_updates": self.home.get_hero_updates()})
        self.assertIn("hero-update-placeholder", html)
        self.assertNotIn('data-glide-el="controls"', html)
        self.assertNotIn("hero-update-pause", html)

    @override_settings(IS_METEOROLOGICAL=True)
    def test_homepage_replaces_product_hero_and_renders_update_controls(self):
        self.news(-1)
        self.event(1)
        response = self.client.get(self.home.url)
        self.assertContains(response, 'id="hero-updates-carousel"')
        self.assertNotContains(response, "Pause updates")
        self.assertNotContains(response, "hero-updates-heading")
        self.assertNotContains(response, "hero-update-summary")
        self.assertNotContains(response, "Next update")
        self.assertNotContains(response, 'id="hero-product-carousel"')

    def test_empty_widget_has_no_markup(self):
        html = render_to_string("home/section/hero_updates_widget.html", {"hero_updates": []})
        self.assertEqual(html.strip(), "")

    def test_latest_el_nino_bulletin_links_to_landing_page(self):
        product_index = ProductIndexPageFactory(parent=self.home)
        el_nino_page = ElNinoPageFactory(parent=product_index)
        older = ProductItemPageFactory(parent=el_nino_page, title="El Niño Bulletin — July")
        latest = ProductItemPageFactory(parent=el_nino_page, title="El Niño Bulletin — August")
        type(older).objects.filter(pk=older.pk).update(date=timezone.localdate() - timedelta(days=35))
        type(latest).objects.filter(pk=latest.pk).update(date=timezone.localdate())

        slides = self.home.get_hero_updates()

        self.assertEqual(slides[0]["kind"], "el_nino")
        self.assertEqual(slides[0]["title"], latest.title)
        self.assertEqual(slides[0]["url"], el_nino_page.url)

    def test_carousel_order_is_news_el_nino_heat_ews_then_summer_school(self):
        latest_news = self.news(-1)
        product_index = ProductIndexPageFactory(parent=self.home)
        el_nino_page = ElNinoPageFactory(parent=product_index)
        ProductItemPageFactory(parent=el_nino_page)
        heat_page = ProductPageFactory(
            parent=product_index,
            title="Heat and Thermal Stress",
            slug="heat-and-thermal-stress",
        )
        ProductItemPageFactory(parent=heat_page)
        summer_school_index = SummerSchoolIndexPageFactory(parent=self.home)
        summer_school = SummerSchoolPageFactory(parent=summer_school_index)

        slides = self.home.get_hero_updates()

        self.assertEqual(
            [slide["kind"] for slide in slides],
            ["news", "el_nino", "heat_ews", "summer_school"],
        )
        self.assertEqual(slides[0]["id"], latest_news.pk)
        self.assertEqual(slides[1]["url"], el_nino_page.url)
        self.assertEqual(slides[2]["url"], heat_page.url)
        self.assertEqual(slides[3]["url"], summer_school_index.url)
        self.assertEqual(slides[3]["title"], summer_school.hero_heading)
