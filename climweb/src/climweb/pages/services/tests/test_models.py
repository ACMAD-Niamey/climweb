from django.urls import reverse
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import NavigationSettings
from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.partners.tests.factories import PartnerFactory
from .factories import (
    RCCClimateProductsPageFactory,
    RCCDataServicesPageFactory,
    ServiceIndexPageFactory,
    ServicePageFactory,
)


class TestServicesPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.index_page = ServiceIndexPageFactory(parent=home_page)
        cls.service1_page = ServicePageFactory(parent=cls.index_page)
        cls.service2_page = ServicePageFactory(parent=cls.index_page)
    
    def test_index_page_render(self):
        self.assertPageIsRenderable(self.index_page)
    
    def test_index_page_meta_tags(self):
        resp = self.client.get(self.index_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.index_page, meta_tags, request=resp.wsgi_request)
    
    def test_news_page_render(self):
        self.assertPageIsRenderable(self.service1_page)
        self.assertPageIsRenderable(self.service2_page)

    def test_service_introduction_title_is_optional(self):
        title_field = self.service1_page._meta.get_field("introduction_title")

        self.assertTrue(title_field.blank)

        self.service1_page.introduction_title = ""
        self.service1_page.save_revision().publish()

        response = self.client.get(self.service1_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<h2 class="intro-title"></h2>', html=True)
    
    def test_news_page_meta_tags(self):
        resp = self.client.get(self.service1_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.service1_page, meta_tags, request=resp.wsgi_request)
        
        resp = self.client.get(self.service2_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.service2_page, meta_tags, request=resp.wsgi_request)

    def test_rcc_service_uses_dedicated_landing_page(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center",
            service__name="Regional Climate Center",
        )

        response = self.client.get(rcc_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_service_page.html")
        self.assertContains(response, "Regional Climate Center products")
        self.assertContains(response, "Climate data services for Africa")
        self.assertContains(response, 'class="page-hero')
        self.assertNotContains(response, 'class="rcc-section-nav"')
        self.assertContains(response, 'id="multi-hazard-map"')
        self.assertContains(response, "Multi-Hazard Map")
        self.assertContains(response, "https://multi-hazard.acmad.org/geoportal")
        self.assertContains(response, "Observations and station data")
        self.assertContains(response, "Gridded climate data")
        self.assertContains(response, "Climate models and projections")
        self.assertContains(response, "Operational tools and guidance")
        self.assertContains(response, 'href="/on-the-job-training/"')

    def test_rcc_pages_use_dedicated_main_menu(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center navigation",
            service__name="Regional Climate Center",
        )
        data_page = RCCDataServicesPageFactory(parent=rcc_page)
        products_page = RCCClimateProductsPageFactory(parent=rcc_page)

        for url in (rcc_page.get_url(), data_page.get_url(), products_page.get_url()):
            response = self.client.get(url)

            self.assertContains(response, "data-rcc-main-menu")
            self.assertContains(response, f'href="{rcc_page.url}">Home</a>')
            self.assertContains(response, f'href="{products_page.url}">Climate Products</a>')
            self.assertContains(response, f'href="{data_page.url}">Data Services</a>')
            self.assertContains(response, f'href="{rcc_page.url}#rcc-resources"')
            self.assertContains(response, "Forums & Training")

        dataset_response = self.client.get(reverse("rcc_dataset_category"))
        self.assertContains(dataset_response, "data-rcc-main-menu")
        self.assertContains(dataset_response, f'href="{rcc_page.url}">Home</a>')

        main_site = Site.objects.get(is_default_site=True)
        self.assertContains(
            dataset_response,
            f'data-main-site-logo href="{main_site.root_url}"',
        )

    def test_rcc_main_menu_can_be_configured_in_navigation_settings(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center configurable navigation",
            service__name="Regional Climate Center",
        )
        data_page = RCCDataServicesPageFactory(parent=rcc_page)
        navigation = NavigationSettings.for_site(Site.objects.get(is_default_site=True))
        navigation.rcc_main_menu = [
            (
                "navigation_item",
                {
                    "label": "RCC Data Catalogue",
                    "page": data_page,
                    "external_url": "",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        response = self.client.get(rcc_page.get_url())

        self.assertContains(response, "RCC Data Catalogue")
        self.assertContains(response, f'href="{data_page.url}"')
        self.assertNotContains(response, "Climate Monitoring")

    def test_non_rcc_service_does_not_use_rcc_main_menu(self):
        response = self.client.get(self.service1_page.get_url())

        self.assertNotContains(response, "data-rcc-main-menu")

    def test_other_services_keep_default_template(self):
        response = self.client.get(self.service1_page.get_url())

        self.assertTemplateUsed(response, "services/service_page.html")
        self.assertTemplateNotUsed(response, "services/rcc_service_page.html")

    def test_rcc_page_displays_featured_partners(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center partners",
            service__name="Regional Climate Center",
        )
        partner = PartnerFactory(visible_on_homepage=True)

        response = self.client.get(rcc_page.get_url())

        self.assertContains(response, "Our partners")
        self.assertContains(response, partner.name)
        self.assertContains(response, 'class="partner-card"')

    def test_rcc_data_services_page_renders_catalogue(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center data parent",
            service__name="Regional Climate Center",
        )
        data_page = RCCDataServicesPageFactory(parent=rcc_page)

        response = self.client.get(data_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_data_services_page.html")
        self.assertContains(response, "Observations and station data")
        self.assertContains(response, "ARC2 estimated rainfall")
        self.assertNotContains(response, "Open access")
        self.assertNotContains(response, "Verified")
        self.assertNotContains(response, "Format")
        self.assertContains(response, 'class="rcc-ds-card__icon"')
        self.assertContains(response, 'id="icon-location"')
        self.assertContains(response, 'class="page-hero rcc-ds-simple-hero"')
        self.assertNotContains(response, 'class="rcc-ds-nav"')
        self.assertNotContains(response, '>Access guide</a>')
        self.assertNotContains(response, "Know before you open a dataset")
        self.assertNotContains(response, "One catalogue for regional climate data")
        self.assertNotContains(response, 'href="#observations"')

    def test_rcc_landing_page_links_to_data_services_catalogue(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center data link",
            service__name="Regional Climate Center",
        )
        data_page = RCCDataServicesPageFactory(parent=rcc_page)

        response = self.client.get(rcc_page.get_url())

        self.assertContains(response, data_page.url)
        self.assertContains(response, "Browse the data catalogue")
        self.assertContains(response, f'href="{data_page.url}#observations"')
        self.assertContains(response, f'href="{data_page.url}#gridded-data"')
        self.assertContains(response, f'href="{data_page.url}#models"')
        self.assertContains(response, f'href="{data_page.url}#tools-guidance"')

    def test_rcc_climate_products_page_renders_and_is_linked(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center products parent",
            service__name="Regional Climate Center",
        )
        products_page = RCCClimateProductsPageFactory(parent=rcc_page)

        response = self.client.get(products_page.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_climate_products_page.html")
        self.assertContains(response, "RCC climate product catalogue")
        self.assertNotContains(response, 'class="rcc-section-nav"')

        landing_response = self.client.get(rcc_page.get_url())
        self.assertContains(landing_response, products_page.url)

    def test_rcc_climate_products_introduction_title_is_optional(self):
        page_model = RCCClimateProductsPageFactory._meta.model
        title_field = page_model._meta.get_field("introduction_title")
        text_field = page_model._meta.get_field("introduction_text")

        self.assertTrue(title_field.blank)
        self.assertTrue(text_field.blank)
