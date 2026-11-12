from django.core.management import call_command
from django.core.management.base import CommandError
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.climsa.models import ClimsaAboutPage, ClimsaHomePage
from climweb.pages.home.tests.factories import get_or_create_homepage


class TestClimsaHomePage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.main_home = get_or_create_homepage()
        cls.page = ClimsaHomePage(title="CLIMSA", slug="climsa")
        cls.main_home.add_child(instance=cls.page)
        cls.page.save_revision().publish()
        cls.site = Site.objects.create(
            hostname="climsa.test",
            port=80,
            site_name="ACMAD CLIMSA",
            root_page=cls.page,
            is_default_site=False,
        )

    def test_subdomain_renders_climsa_home_and_contextual_navigation(self):
        response = self.client.get("/", HTTP_HOST="climsa.test")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "climsa/climsa_home_page.html")
        self.assertContains(response, "section-climsa")
        self.assertContains(response, "css/climsa.css")
        self.assertContains(response, "About Us")
        self.assertContains(response, "Publications")
        self.assertContains(response, "Project Outputs")
        self.assertContains(response, "Continental Steering Committees")
        self.assertContains(response, "Climate-informed decisions")

    def test_flex_pages_are_allowed_beneath_climsa(self):
        self.assertIn("flex_page.FlexPage", self.page.subpage_types)

    def test_about_page_renders_programme_content(self):
        about_page = ClimsaAboutPage(title="About Us", slug="about")
        self.page.add_child(instance=about_page)
        about_page.save_revision().publish()
        self.page.about_page = about_page
        self.page.save_revision().publish()

        response = self.client.get("/about/", HTTP_HOST="climsa.test")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "climsa/climsa_about_page.html")
        self.assertContains(response, "About the programme")
        self.assertContains(response, "ACMAD&#x27;s five project outputs")
        self.assertContains(response, "Download factsheet")
        self.assertContains(
            response,
            "Establishing structured user interfaces for agriculture, water, health, and disaster management.",
        )

    def test_configure_command_creates_and_links_about_page(self):
        call_command(
            "configure_climsa_subdomain",
            hostname="climsa.test",
            port=80,
            create=True,
        )

        self.page.refresh_from_db()
        self.assertIsNotNone(self.page.about_page_id)
        self.assertEqual(self.page.about_page.slug, "about")
        self.assertTrue(self.page.about_page.live)

    def test_configure_command_rejects_a_url_as_hostname(self):
        with self.assertRaises(CommandError):
            call_command(
                "configure_climsa_subdomain",
                hostname="https://climsa.test/",
            )

    def test_configure_command_reconciles_existing_site(self):
        call_command(
            "configure_climsa_subdomain",
            hostname="climsa.test",
            port=443,
        )

        self.site.refresh_from_db()
        self.assertEqual(self.site.port, 443)
        self.assertEqual(self.site.root_page_id, self.page.pk)
        self.assertFalse(self.site.is_default_site)
