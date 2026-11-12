from io import StringIO

from django.core.management import call_command
from django.test import RequestFactory
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import ServiceCategory
from climweb.base.templatetags.nmhs_cms_tags import climate_health_navigation
from climweb.pages.climate_health.models import (
    ClimateHealthAboutPage,
    ClimateHealthContentPage,
    ClimateHealthDeskHomePage,
    ClimateHealthPolicyPage,
)
from climweb.pages.services.tests.factories import ServiceIndexPageFactory


class ClimateHealthDeskTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        ServiceIndexPageFactory()

    def test_bootstrap_creates_complete_subsite_and_is_idempotent(self):
        for _ in range(2):
            call_command(
                "bootstrap_climate_health_desk",
                hostname="health.example.test",
                port=443,
                stdout=StringIO(),
            )

        desk = ClimateHealthDeskHomePage.objects.get()
        self.assertTrue(desk.live)
        self.assertEqual(
            set(
                ClimateHealthContentPage.objects.child_of(desk).values_list(
                    "listing_type", flat=True
                )
            ),
            {"products", "publications", "platforms", "events"},
        )
        self.assertEqual(
            ClimateHealthPolicyPage.objects.child_of(desk).count(), 1
        )
        self.assertEqual(
            ClimateHealthAboutPage.objects.child_of(desk).count(), 1
        )
        self.assertEqual(desk.partner_links.count(), 6)
        self.assertEqual(desk.platform_links.count(), 2)
        self.assertEqual(desk.priorities.count(), 4)
        self.assertTrue(
            ServiceCategory.objects.filter(name="Climate and Health").exists()
        )

        site = Site.objects.get(hostname="health.example.test")
        self.assertEqual(site.root_page_id, desk.pk)
        self.assertFalse(site.is_default_site)

    def test_health_hostname_uses_dedicated_navigation(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )

        desk = ClimateHealthDeskHomePage.objects.get()
        request = RequestFactory().get("/", HTTP_HOST="health.example.test")
        navigation = climate_health_navigation({"request": request, "page": desk})

        self.assertEqual(navigation["home_url"], "/")
        self.assertEqual(navigation["about_url"], "/about/")
        self.assertEqual(navigation["products_url"], "/products/")
        self.assertEqual(navigation["publications_url"], "/publications/")
        self.assertEqual(navigation["platforms_url"], "/platforms/")
        self.assertEqual(navigation["events_url"], "/events/")
        self.assertEqual(
            navigation["policies_url"], "/action-plan-policies/"
        )
