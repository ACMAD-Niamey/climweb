from datetime import date
from io import StringIO

from django.core.management import call_command
from django.urls import reverse
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import NavigationSettings
from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.partners.tests.factories import PartnerFactory
from climweb.pages.products.tests.factories import (
    ProductIndexPageFactory,
    ProductItemPageFactory,
    ProductPageFactory,
)
from climweb.pages.services.long_range_forums import CONSENSUS_FORUMS
from .factories import (
    RCCClimateMonitoringPageFactory,
    RCCConsensusForumPageFactory,
    RCCClimateProductsPageFactory,
    RCCDataServicesPageFactory,
    RCCLongRangeForecastingPageFactory,
    RCCRecommendedFunctionsPageFactory,
    RCCTrainingPageFactory,
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

    def test_rcc_data_services_links_rdt_and_itd_to_local_product_pages(self):
        home_page = get_or_create_homepage()
        product_index = ProductIndexPageFactory(parent=home_page)
        rdt_page = ProductPageFactory(
            parent=product_index,
            title="Thunderstorm and Nowcasting",
            slug="thunderstorm-and-nowcasting",
        )
        itd_page = ProductPageFactory(
            parent=product_index,
            title="ITD and ITCZ Monitoring",
            slug="itd-and-itcz-monitoring",
        )
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center local archives",
            service__name="Regional Climate Center",
        )
        data_page = RCCDataServicesPageFactory(
            parent=rcc_page,
            data_groups=[
                (
                    "group",
                    {
                        "anchor": "tools-guidance",
                        "title": "Operational tools and guidance",
                        "summary": "Operational archives.",
                        "icon": "cogs",
                        "datasets": [
                            {
                                "title": "Rapidly Developing Thunderstorm data",
                                "description": "RDT products.",
                                "access_type": "archive",
                                "local_dataset_key": "thunderstorm-nowcasting",
                            },
                            {
                                "title": "Intertropical Discontinuity monitoring",
                                "description": "ITD products.",
                                "access_type": "archive",
                                "local_dataset_key": "itd-itcz",
                            },
                        ],
                    },
                )
            ],
        )

        response = self.client.get(data_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{rdt_page.url}"')
        self.assertContains(response, f'href="{itd_page.url}"')
        self.assertNotContains(response, "sgbd.acmad.org")
        self.assertNotContains(response, "thredds")

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

    def test_rcc_climate_monitoring_page_renders_and_is_linked(self):
        product_index = ProductIndexPageFactory(parent=get_or_create_homepage())
        annual_page = ProductPageFactory(
            parent=product_index,
            title="Annual State of the Climate Report",
            slug="annual-state-of-the-climate-report",
        )
        monthly_page = ProductPageFactory(
            parent=product_index,
            title="Monthly Climate Diagnostic Bulletin",
            slug="monthly-climate-diagnostic-bulletin",
        )
        dekadal_page = ProductPageFactory(
            parent=product_index,
            title="Dekadal Weather Forecast",
            slug="dekadal-weather-forecast",
        )
        additional_product_pages = {
            slug: ProductPageFactory(
                parent=product_index,
                title=title,
                slug=slug,
            )
            for slug, title in (
                ("daily-rainfall-monitoring", "Daily Rainfall Monitoring"),
                (
                    "rainfall-and-seasonal-onset-monitoring",
                    "Rainfall and Seasonal Onset Monitoring",
                ),
                ("climate-watch-bulletin", "Climate Watch Bulletin"),
                ("atmospheric-analysis", "Atmospheric Analysis"),
                ("itd-and-itcz-monitoring", "ITD and ITCZ Monitoring"),
                (
                    "cryosphere-and-african-mountain-glaciers",
                    "Cryosphere and African Mountain Glaciers",
                ),
            )
        }
        ProductItemPageFactory(
            parent=annual_page,
            title="Annual assessment 2025",
            date=date(2025, 12, 31),
        )
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center monitoring parent",
            service__name="Regional Climate Center",
        )
        monitoring_page = RCCClimateMonitoringPageFactory(parent=rcc_page)

        response = self.client.get(monitoring_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "services/rcc_climate_monitoring_page.html",
        )
        self.assertContains(response, "Monitoring Africa&#x27;s climate system")
        self.assertContains(response, "Temperature")
        self.assertContains(response, "Precipitation")
        self.assertContains(response, "Atmospheric circulation")
        self.assertContains(response, "Convection")
        self.assertContains(response, "Climate diagnostics and assessment")
        self.assertContains(response, f'href="{annual_page.url}"')
        self.assertContains(response, f'href="{monthly_page.url}"')
        self.assertContains(response, f'href="{dekadal_page.url}"')
        for product_page in additional_product_pages.values():
            self.assertContains(response, f'href="{product_page.url}"')
        self.assertContains(response, "31 Dec 2025")
        self.assertContains(response, "Rainfall and seasonal onset monitoring")
        self.assertContains(
            response,
            "Climate watch, extremes and atmospheric conditions",
        )
        self.assertContains(response, "Country monitoring")
        self.assertContains(response, "Africa/africa_multimodele.html")
        self.assertContains(response, "Niger/niger_multimodele.html")
        self.assertContains(response, "Country monitoring forecast viewers")
        self.assertContains(response, "Climate indices and historical trends")
        self.assertContains(response, "Reference climatologies and historical observations")
        self.assertContains(response, "Cryosphere and African Mountain Glaciers")
        self.assertContains(response, "Monitoring data and analysis tools")
        self.assertContains(response, f'href="{reverse("rcc_climate_index_gallery")}"')
        self.assertContains(response, f'href="{reverse("rcc_seasonal_map_gallery")}"')
        self.assertContains(
            response,
            f'href="{reverse("rcc_reference_climatology_countries")}"',
        )
        self.assertContains(response, f'href="{reverse("rcc_dataset_category")}"')
        self.assertContains(response, f'href="{reverse("rcc_cpc_dataset_category")}"')
        self.assertContains(response, f'href="{monitoring_page.url}"')
        self.assertContains(response, "sgbd.acmad.org")
        self.assertContains(response, "THREDDS")

    def test_climate_monitoring_seed_links_existing_custom_menu_item(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center monitoring menu",
            service__name="Regional Climate Center",
        )
        products_page = RCCClimateProductsPageFactory(parent=rcc_page)
        monitoring_page = RCCClimateMonitoringPageFactory(parent=rcc_page)
        navigation = NavigationSettings.for_site(Site.objects.get(is_default_site=True))
        navigation.rcc_main_menu = [
            (
                "navigation_item",
                {
                    "label": "Climate Monitoring",
                    "page": products_page,
                    "external_url": "",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        call_command("seed_rcc_climate_monitoring", stdout=StringIO())

        navigation.refresh_from_db()
        menu_item = navigation.rcc_main_menu[0].value
        self.assertEqual(menu_item["page"].pk, monitoring_page.pk)
        self.assertEqual(menu_item["external_url"], "")

    def test_rcc_long_range_forecasting_page_uses_local_archives(self):
        product_index = ProductIndexPageFactory(parent=get_or_create_homepage())
        product_pages = {}
        for slug, title in (
            ("seasonal-forecast-maps", "Seasonal Forecast Maps"),
            ("seasonal-outlook-bulletins", "Seasonal Outlook Bulletins"),
            (
                "seasonal-consensus-statements-and-communiques",
                "Consensus Statements and Communiqués",
            ),
            (
                "seasonal-recommendations-and-summaries",
                "Recommendations and Summaries",
            ),
            ("seasonal-technical-notes", "Technical Notes"),
            ("seasonal-model-performance", "Seasonal Model Performance"),
            ("seasonal-forecast-verification", "Seasonal Forecast Verification"),
        ):
            product_pages[slug] = ProductPageFactory(
                parent=product_index,
                slug=slug,
                title=title,
            )

        ProductItemPageFactory(
            parent=product_pages["seasonal-forecast-maps"],
            title="Seasonal map",
            date=date(2026, 9, 1),
        )
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center long-range parent",
            service__name="Regional Climate Center",
        )
        forecasting_page = RCCLongRangeForecastingPageFactory(parent=rcc_page)
        forum_pages = {}
        for forum in CONSENSUS_FORUMS:
            forum_pages[forum["slug"]] = RCCConsensusForumPageFactory(
                parent=forecasting_page,
                title=str(forum["name"]),
                slug=forum["slug"],
                banner_title=str(forum["name"]),
                forum_code=forum["code"],
                region=str(forum["region"]),
                target_season=str(forum["season"]),
                summary=str(forum["summary"]),
                archive_codes=",".join(forum["document_codes"]),
            )

        response = self.client.get(forecasting_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "services/rcc_long_range_forecasting_page.html",
        )
        self.assertContains(response, "Seasonal forecast products")
        self.assertContains(response, "Performance and verification")
        self.assertContains(
            response,
            "Tailored Precipitation and Temperature Forecasts",
        )
        self.assertContains(response, "Statistical and Dynamical Model Performance")
        self.assertContains(response, "Forecast and Outlook Verification")
        self.assertContains(response, "Climate Outlook Forums")
        gallery_slugs = {
            "seasonal-forecast-maps",
            "seasonal-consensus-statements-and-communiques",
            "seasonal-model-performance",
            "seasonal-forecast-verification",
        }
        for slug, product_page in product_pages.items():
            if slug in gallery_slugs:
                continue
            self.assertContains(response, f'href="{product_page.url}"')
        for url_name in (
            "rcc_tailored_forecast_gallery",
            "rcc_model_performance_gallery",
            "rcc_forecast_verification_gallery",
        ):
            gallery_url = reverse(url_name)
            self.assertContains(response, f'href="{gallery_url}"')
            gallery_response = self.client.get(gallery_url)
            self.assertEqual(gallery_response.status_code, 200)
            self.assertTemplateUsed(
                gallery_response,
                "services/rcc_long_range_gallery.html",
            )
        consensus_url = reverse("rcc_consensus_forums")
        self.assertContains(response, f'href="{consensus_url}"')
        consensus_response = self.client.get(consensus_url)
        self.assertEqual(consensus_response.status_code, 200)
        self.assertTemplateUsed(
            consensus_response,
            "services/rcc_consensus_forums.html",
        )
        for forum in ("accof", "presao", "presass", "presac", "presagg", "medcof", "swiocof", "sarcof", "ghacof"):
            detail_url = reverse("rcc_consensus_forum_detail", args=[forum])
            self.assertContains(
                consensus_response,
                f'href="{forum_pages[forum].url}"',
            )
            detail_response = self.client.get(detail_url)
            self.assertEqual(detail_response.status_code, 200)
            self.assertTemplateUsed(
                detail_response,
                "services/rcc_consensus_forum_detail.html",
            )
        self.assertEqual(
            self.client.get(
                reverse("rcc_consensus_forum_detail", args=["unknown-forum"])
            ).status_code,
            404,
        )
        self.assertNotContains(response, "sgbd.acmad.org")
        self.assertNotContains(response, "rcc.acmad.org")

    def test_long_range_forecasting_seed_links_existing_menu_item(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center long-range menu",
            service__name="Regional Climate Center",
        )
        products_page = RCCClimateProductsPageFactory(parent=rcc_page)
        forecasting_page = RCCLongRangeForecastingPageFactory(parent=rcc_page)
        navigation = NavigationSettings.for_site(Site.objects.get(is_default_site=True))
        navigation.rcc_main_menu = [
            (
                "navigation_item",
                {
                    "label": "Long-range Forecasting",
                    "page": products_page,
                    "external_url": "",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        call_command("seed_rcc_long_range_forecasting", stdout=StringIO())

        navigation.refresh_from_db()
        menu_item = navigation.rcc_main_menu[0].value
        self.assertEqual(menu_item["page"].pk, forecasting_page.pk)
        self.assertEqual(menu_item["external_url"], "")

    def test_rcc_climate_products_introduction_title_is_optional(self):
        page_model = RCCClimateProductsPageFactory._meta.model
        title_field = page_model._meta.get_field("introduction_title")
        text_field = page_model._meta.get_field("introduction_text")

        self.assertTrue(title_field.blank)
        self.assertTrue(text_field.blank)

    def test_rcc_training_page_renders_complete_training_structure(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center training parent",
            service__name="Regional Climate Center",
        )
        training_page = RCCTrainingPageFactory(parent=rcc_page)

        response = self.client.get(training_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_training_page.html")
        self.assertContains(response, "Programmes and learning activities")
        self.assertContains(response, "Methods, tools and guidance")
        self.assertContains(response, "Workshop, training and survey reports")
        self.assertContains(response, "Seasonal forecast training series")
        self.assertContains(response, "Climate data services")
        self.assertContains(response, "Workshops and seminars")
        self.assertContains(response, "CucEP23gWfU")

    def test_rcc_training_seed_links_existing_menu_item(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center training menu",
            service__name="Regional Climate Center",
        )
        products_page = RCCClimateProductsPageFactory(parent=rcc_page)
        navigation = NavigationSettings.for_site(Site.objects.get(is_default_site=True))
        navigation.rcc_main_menu = [
            (
                "navigation_item",
                {
                    "label": "Training",
                    "page": products_page,
                    "external_url": "",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        call_command("seed_rcc_training", stdout=StringIO())

        training_page = RCCTrainingPageFactory._meta.model.objects.child_of(
            rcc_page
        ).get()
        navigation.refresh_from_db()
        menu_item = navigation.rcc_main_menu[0].value
        self.assertEqual(menu_item["page"].pk, training_page.pk)
        self.assertEqual(menu_item["external_url"], "")

    def test_rcc_recommended_functions_page_renders_all_sections(self):
        product_index = ProductIndexPageFactory(parent=get_or_create_homepage())
        report_product = ProductPageFactory(
            parent=product_index,
            title="Climate Change and Climate Projections",
            slug="climate-change-and-climate-projections",
        )
        report_item = ProductItemPageFactory(
            parent=report_product,
            title="Climate variability and risk study",
            date=date(2014, 2, 20),
        )
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center recommended functions parent",
            service__name="Regional Climate Center",
        )
        page = RCCRecommendedFunctionsPageFactory(parent=rcc_page)

        response = self.client.get(page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "services/rcc_recommended_functions_page.html",
        )
        self.assertContains(response, "Functions and outputs")
        self.assertContains(response, "Climate-change indices")
        self.assertContains(response, "Research reports and climate-change evidence")
        self.assertContains(response, report_item.title)
        self.assertContains(response, f'href="{report_item.url}"')
        self.assertNotContains(response, "Climate-change indices for African stations")
        self.assertContains(response, 'href="https://example.com/climate-indices/"')

    def test_rcc_recommended_functions_seed_links_menu_item(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center recommended functions menu",
            service__name="Regional Climate Center",
        )
        products_page = RCCClimateProductsPageFactory(parent=rcc_page)
        navigation = NavigationSettings.for_site(Site.objects.get(is_default_site=True))
        navigation.rcc_main_menu = [
            (
                "navigation_item",
                {
                    "label": "Highly Recommended Functions",
                    "page": products_page,
                    "external_url": "",
                    "include_subpages": False,
                    "large_submenu": False,
                    "sub_items": [],
                },
            )
        ]
        navigation.save()

        call_command("seed_rcc_recommended_functions", stdout=StringIO())

        page = RCCRecommendedFunctionsPageFactory._meta.model.objects.child_of(
            rcc_page
        ).get()
        navigation.refresh_from_db()
        menu_item = navigation.rcc_main_menu[0].value
        self.assertEqual(menu_item["page"].pk, page.pk)
        self.assertEqual(menu_item["external_url"], "")
