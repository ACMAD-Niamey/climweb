from io import StringIO

from django.core.management import call_command
from django.test import RequestFactory
from wagtail.models import Site
from wagtail.snippets.widgets import AdminSnippetChooser
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import NavigationSettings, ServiceCategory
from climweb.base.templatetags.nmhs_cms_tags import climate_health_navigation
from climweb.pages.climate_health.models import (
    ClimateHealthAboutPage,
    ClimateHealthContentPage,
    ClimateHealthDeskHomePage,
    ClimateHealthPartnerLink,
    ClimateHealthPolicyPage,
    ClimateHealthProductLink,
)
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.partners.tests.factories import PartnerFactory
from climweb.pages.products.tests.factories import (
    ProductIndexPageFactory,
    ProductPageFactory,
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

    def test_homepage_features_up_to_five_products_and_platforms(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )

        desk = ClimateHealthDeskHomePage.objects.get()
        site = Site.objects.get(hostname="health.example.test")
        request = RequestFactory().get("/", HTTP_HOST=site.hostname)
        request.site = site
        desk.__dict__.update(
            products=list(range(6)),
            news=[],
            events=[],
            platforms=list(range(6)),
            partners=[],
        )

        context = desk.get_context(request)

        self.assertEqual(context["featured_products"], list(range(5)))
        self.assertEqual(context["featured_platforms"], list(range(5)))

    def test_homepage_products_follow_editor_order(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )
        desk = ClimateHealthDeskHomePage.objects.get()
        product_index = ProductIndexPageFactory(parent=get_or_create_homepage())
        products = [
            ProductPageFactory(parent=product_index, title=f"Health product {index}")
            for index in range(3)
        ]
        for sort_order, product in enumerate(reversed(products)):
            ClimateHealthProductLink.objects.create(
                page=desk,
                product=product,
                sort_order=sort_order,
            )

        self.assertEqual(desk.homepage_products, list(reversed(products)))

    def test_partners_follow_page_order_and_appear_on_about_page(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )
        desk = ClimateHealthDeskHomePage.objects.get()
        desk.partner_links.all().delete()
        partners = [
            PartnerFactory(name="Partner Alpha", order=1),
            PartnerFactory(name="Partner Beta", order=999),
            PartnerFactory(name="Partner Gamma", order=50),
        ]
        display_order = [partners[1], partners[2], partners[0]]
        for sort_order, partner in enumerate(display_order):
            ClimateHealthPartnerLink.objects.create(
                page=desk,
                partner=partner,
                sort_order=sort_order,
            )

        self.assertEqual(desk.partners, display_order)

        site = Site.objects.get(hostname="health.example.test")
        response = self.client.get("/about/", HTTP_HOST=site.hostname)
        content = response.content.decode()
        self.assertContains(response, desk.partners_section_title)
        self.assertLess(
            content.index("Partner Beta"),
            content.index("Partner Gamma"),
        )
        self.assertLess(
            content.index("Partner Gamma"),
            content.index("Partner Alpha"),
        )

    def test_partner_selector_uses_complete_snippet_chooser(self):
        partner_panel = ClimateHealthPartnerLink.panels[0]

        self.assertIsInstance(partner_panel.widget, AdminSnippetChooser)

    def test_homepage_map_exposes_meningitis_and_heat_index_tabs(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )
        site = Site.objects.get(hostname="health.example.test")

        response = self.client.get("/", HTTP_HOST=site.hostname)

        self.assertContains(
            response,
            'data-dataset-ids="meningitis-vigilance-weeky|heat-index-valid-24"',
        )
        self.assertContains(
            response,
            'data-dataset-labels="Meningitis Vigilance Outlook|Heat Index"',
        )
        self.assertNotContains(response, 'data-hide-tabs="true"')
        self.assertContains(
            response,
            'id="multi-hazard-viewer-link"',
        )
        self.assertContains(
            response,
            'href="https://multi-hazard.acmad.org/geoportal?dataset=meningitis-vigilance-weeky"',
        )

    def test_map_viewer_deep_link_preserves_existing_query_parameters(self):
        desk = ClimateHealthDeskHomePage(
            map_viewer_url="https://multi-hazard.acmad.org/geoportal?lang=fr",
            map_meningitis_dataset_id="meningitis-vigilance-weeky",
        )

        self.assertEqual(
            desk.map_viewer_deep_link,
            "https://multi-hazard.acmad.org/geoportal?lang=fr&dataset=meningitis-vigilance-weeky",
        )

    def test_health_main_menu_can_be_configured_in_navigation_settings(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )

        site = Site.objects.get(hostname="health.example.test")
        navigation = NavigationSettings.for_site(site)
        navigation.climate_health_main_menu = [
            (
                "navigation_item",
                {
                    "label": "Health Data Hub",
                    "page": None,
                    "external_url": "https://example.test/health-data/",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        response = self.client.get("/", HTTP_HOST=site.hostname)

        self.assertContains(response, "Health Data Hub")
        self.assertContains(response, 'href="https://example.test/health-data/"')
        self.assertNotContains(response, ">Action Plan &amp; Policies</a>")

    def test_health_main_menu_uses_main_site_setting_as_fallback(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )

        health_site = Site.objects.get(hostname="health.example.test")
        main_site = Site.objects.get(is_default_site=True)
        navigation = NavigationSettings.for_site(main_site)
        navigation.climate_health_main_menu = [
            (
                "navigation_item",
                {
                    "label": "Main Dashboard Health Menu",
                    "page": None,
                    "external_url": "https://example.test/main-health-menu/",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        response = self.client.get("/", HTTP_HOST=health_site.hostname)

        self.assertContains(response, "Main Dashboard Health Menu")
        self.assertContains(
            response, 'href="https://example.test/main-health-menu/"'
        )

    def test_fallback_health_menu_has_working_links(self):
        call_command(
            "bootstrap_climate_health_desk",
            hostname="health.example.test",
            port=80,
            stdout=StringIO(),
        )

        site = Site.objects.get(hostname="health.example.test")
        response = self.client.get("/", HTTP_HOST=site.hostname)

        self.assertContains(response, 'href="/about/">About</a>')
        self.assertContains(response, 'href="/products/">Products</a>')
        self.assertContains(response, 'href="/platforms/">Platforms</a>')
        self.assertContains(
            response,
            'href="/action-plan-policies/">Action Plan & Policies</a>',
        )
