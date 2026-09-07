from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import FAQSettings
from climweb.pages.home.tests.factories import get_or_create_homepage


class TestFAQSettings(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = get_or_create_homepage()
        cls.site = Site.objects.get(is_default_site=True)

    def test_default_settings_include_generated_faq_items(self):
        faq_settings = FAQSettings(site=self.site)

        self.assertTrue(faq_settings.is_enabled)
        self.assertEqual(len(faq_settings.items), 5)
        self.assertEqual(
            faq_settings.items[0].value["question"],
            "Where can I find the latest weather and climate products?",
        )

        FAQSettings.objects.create(site=self.site)
        response = self.client.get(self.page.url)

        self.assertContains(response, "Where can I find the latest weather and climate products?")
        self.assertContains(response, "Use the Products menu to browse the latest forecasts")

    def test_faq_drawer_uses_dashboard_managed_content(self):
        FAQSettings.objects.create(
            site=self.site,
            navigation_label="Questions",
            heading="How can we help?",
            introduction="Answers maintained by our web team.",
            items=[
                {
                    "type": "faq_item",
                    "value": {
                        "question": "Can editors update this answer?",
                        "answer": "<p>Yes, from FAQ settings in the dashboard.</p>",
                    },
                }
            ],
        )

        response = self.client.get(self.page.url)

        self.assertContains(response, 'class="js-faq-open util-link faq-util-button"')
        self.assertContains(response, "Questions")
        self.assertContains(response, "How can we help?")
        self.assertContains(response, "Answers maintained by our web team.")
        self.assertContains(response, "Can editors update this answer?")
        self.assertContains(response, "Yes, from FAQ settings in the dashboard.")

    def test_disabled_faq_is_not_rendered(self):
        FAQSettings.objects.create(site=self.site, is_enabled=False)

        response = self.client.get(self.page.url)

        self.assertNotContains(response, 'id="site-faq-drawer"')
        self.assertNotContains(response, "js-faq-open")
