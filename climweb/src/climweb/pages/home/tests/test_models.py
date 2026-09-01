from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.products.tests.factories import (
    ProductIndexPageFactory,
    ProductItemPageFactory,
    ProductPageFactory,
)
from climweb.pages.summer_school.tests.factories import (
    SummerSchoolIndexPageFactory,
    SummerSchoolPageFactory,
    SummerSchoolApplicationPageFactory,
)
from climweb.pages.home.models import (
    RegionalClimateCentre,
    canonical_public_page_url,
    get_significant_product_slides,
)
from .factories import get_or_create_homepage


class TestHomePage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = get_or_create_homepage()
    
    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)

    def test_dg_message_uses_homepage_editor_content(self):
        self.page.dg_message_heading = "A message from leadership"
        self.page.dg_message = "Custom dashboard-managed DG message."
        self.page.dg_message_closing = "A custom closing statement."
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "A message from leadership")
        self.assertContains(response, "Custom dashboard-managed DG message.")
        self.assertContains(response, "A custom closing statement.")

    def test_dg_message_section_can_be_hidden(self):
        self.page.show_dg_message = False
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertNotContains(response, 'class="section dg-message-section"')

    def test_regional_climate_centres_are_managed_by_snippets(self):
        RegionalClimateCentre.objects.all().delete()
        RegionalClimateCentre.objects.create(
            display_name="Editable RCC",
            full_name="Editable Regional Climate Centre",
            city="Test City",
            country="Test Country",
            website_url="https://rcc.example.com/",
            status=RegionalClimateCentre.STATUS_DESIGNATED,
            map_x=Decimal("80.0"),
            map_y=Decimal("90.0"),
            label_position=RegionalClimateCentre.LABEL_UPPER_RIGHT,
            is_primary=True,
            order=10,
        )
        RegionalClimateCentre.objects.create(
            display_name="Hidden RCC",
            full_name="Hidden Regional Climate Centre",
            city="Hidden City",
            country="Hidden Country",
            website_url="https://hidden.example.com/",
            status=RegionalClimateCentre.STATUS_DEMONSTRATION,
            map_x=Decimal("100.0"),
            map_y=Decimal("100.0"),
            is_active=False,
            order=20,
        )

        response = self.client.get(self.page.url)

        self.assertContains(response, "Editable RCC")
        self.assertContains(response, "Test City")
        self.assertContains(response, "https://rcc.example.com/")
        self.assertContains(response, "1 RCCs")
        self.assertNotContains(response, "Hidden RCC")

    def test_regional_climate_centre_exposes_marker_geometry(self):
        centre = RegionalClimateCentre(
            display_name="Geometry RCC",
            full_name="Geometry Regional Climate Centre",
            city="Map City",
            country="Map Country",
            website_url="https://geometry.example.com/",
            map_x=Decimal("34.5"),
            map_y=Decimal("15.9"),
            label_position=RegionalClimateCentre.LABEL_UPPER_LEFT,
        )

        self.assertEqual(centre.marker_transform, "translate(34.5 15.9)")
        self.assertEqual(centre.label_geometry["text_anchor"], "end")
        self.assertEqual(centre.marker_title, "Geometry Regional Climate Centre — Map City, Map Country")
    
    def test_default_seo_image(self):
        self.assertEqual(self.page.get_meta_image(), self.page.hero_banner)
    
    def test_get_context_with_request(self):
        context = self.page.get_context(self.dummy_request)

        self.assertIn("country_bounds", context)
        self.assertIn("city_search_url", context)
        self.assertIn("home_weather_widget_url", context)

        # The met-mode homepage renders the multi-hazard map widget instead of
        # the legacy Vue home-map, so which settings url shows up in the
        # context depends on IS_METEOROLOGICAL (see HomePage.get_context).
        if self.page.show_weather_watch:
            if settings.IS_METEOROLOGICAL:
                self.assertIn("multi_hazard_api_base_url", context)
                self.assertIn("multi_hazard_project_slug", context)
            else:
                self.assertIn("home_map_settings_url", context)

        if self.page.youtube_playlist:
            self.assertIn("youtube_playlist_url", context)
    
    def test_meta_tags(self):
        resp = self.client.get(self.page.full_url)
        
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)

    def test_flagged_products_use_configured_homepage_order(self):
        product_index = ProductIndexPageFactory(parent=self.page)
        later_product = ProductPageFactory(
            parent=product_index,
            title="Later featured product",
            is_featured_on_homepage=True,
            homepage_feature_order=20,
        )
        first_product = ProductPageFactory(
            parent=product_index,
            title="First featured product",
            is_featured_on_homepage=True,
            homepage_feature_order=5,
        )
        unordered_product = ProductPageFactory(
            parent=product_index,
            title="Unordered featured product",
            is_featured_on_homepage=True,
        )
        third_product = ProductPageFactory(
            parent=product_index,
            title="Third featured product",
            is_featured_on_homepage=True,
            homepage_feature_order=30,
        )
        fourth_product = ProductPageFactory(
            parent=product_index,
            title="Fourth featured product",
            is_featured_on_homepage=True,
            homepage_feature_order=40,
        )
        ProductPageFactory(
            parent=product_index,
            title="Overflow unordered product",
            is_featured_on_homepage=True,
        )
        ProductPageFactory(
            parent=product_index,
            title="Not featured product",
            is_featured_on_homepage=False,
            homepage_feature_order=1,
        )

        self.page.__dict__.pop("featured_products_list", None)
        featured_titles = [item["title"] for item in self.page.featured_products_list]

        self.assertEqual(
            featured_titles,
            [
                first_product.title,
                later_product.title,
                third_product.title,
                fourth_product.title,
                unordered_product.title,
            ],
        )

    def test_unfeatured_product_is_ignored_when_still_manually_selected(self):
        product_index = ProductIndexPageFactory(parent=self.page)
        product = ProductPageFactory(
            parent=product_index,
            title="Legacy manually selected product",
            is_featured_on_homepage=False,
        )
        self.page.featured_products = [
            {
                "type": "product",
                "value": {
                    "page": product,
                    "custom_title": "",
                    "custom_blurb": "",
                    "icon": "",
                },
            }
        ]

        self.page.__dict__.pop("featured_products_list", None)

        self.assertEqual(self.page.featured_products_list, [])

    def test_significant_product_slides_use_latest_item_from_each_family(self):
        product_index = ProductIndexPageFactory(parent=self.page)
        multi_hazard = ProductPageFactory(
            parent=product_index,
            title="Weather Watch and Prediction Products",
        )
        heat = ProductPageFactory(parent=product_index, title="Heat and Thermal Stress")
        thunderstorm = ProductPageFactory(parent=product_index, title="Thunderstorm and Nowcasting")

        ProductItemPageFactory(
            parent=multi_hazard,
            title="Continental Multi-Hazard Outlook — older",
            date=date(2026, 8, 1),
        )
        ProductItemPageFactory(
            parent=multi_hazard,
            title="Continental Multi-Hazard Outlook — latest",
            date=date(2026, 8, 6),
        )
        ProductItemPageFactory(parent=heat, date=date(2026, 8, 8))
        ProductItemPageFactory(parent=thunderstorm, date=date(2026, 8, 7))

        slides = get_significant_product_slides()

        self.assertEqual([slide["key"] for slide in slides], ["multi-hazard", "heat", "thunderstorm"])
        self.assertEqual(
            [slide["issue_date"] for slide in slides],
            [date(2026, 8, 6), date(2026, 8, 8), date(2026, 8, 7)],
        )

    def test_significant_product_links_hide_internal_homepage_slug(self):
        self.assertEqual(
            canonical_public_page_url("/home-page/products/heat-and-thermal-stress/"),
            "/products/heat-and-thermal-stress/",
        )
        self.assertEqual(canonical_public_page_url("/products/example/"), "/products/example/")

    def test_significant_product_slides_follow_dashboard_selection_order(self):
        product_index = ProductIndexPageFactory(parent=self.page)
        heat = ProductPageFactory(parent=product_index, title="Heat and Thermal Stress")
        thunderstorm = ProductPageFactory(parent=product_index, title="Thunderstorm and Nowcasting")
        ProductItemPageFactory(parent=heat, date=date(2026, 8, 8))
        ProductItemPageFactory(parent=thunderstorm, date=date(2026, 8, 7))

        slides = get_significant_product_slides([thunderstorm, heat])

        self.assertEqual([slide["key"] for slide in slides], ["thunderstorm", "heat"])

    def test_utility_navbar_rotates_latest_items_in_dashboard_order(self):
        product_index = ProductIndexPageFactory(parent=self.page)
        first_family = ProductPageFactory(parent=product_index, title="First utility family")
        second_family = ProductPageFactory(parent=product_index, title="Second utility family")
        first_item = ProductItemPageFactory(
            parent=first_family, title="Latest first utility product", date=date(2026, 8, 30),
        )
        second_item = ProductItemPageFactory(
            parent=second_family, title="Latest second utility product", date=date(2026, 8, 31),
        )
        ProductItemPageFactory(
            parent=first_family, title="Older first utility product", date=date(2026, 8, 1),
        )
        self.page.hero_featured_products = [("product", second_family), ("product", first_family)]
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        content = response.content.decode()
        header = content[content.index('<header class="site-header">'):content.index("</header>")]

        self.assertContains(response, second_item.title)
        self.assertContains(response, first_item.title)
        self.assertNotContains(response, "Older first utility product")
        self.assertLess(content.index(second_item.title), content.index(first_item.title))
        self.assertNotIn("African Regional Climate Centre", header)
        self.assertNotIn("Continental Multi-Hazard Advisory Centre", header)


class TestHomeFeaturedSummerSchool(WagtailPageTestCase):
    """
    The summer school banner (home/section/summer_school_include.html) shows
    an Apply button sourced from edition.application_page - which used to
    silently disappear (no closed-state message) once application_open was
    off or the deadline had passed, and read edition.application_page off a
    property that returned the base Page (see
    SummerSchoolPage.application_page), so is_closed always resolved falsy.
    """

    @classmethod
    def setUpTestData(cls):
        cls.page = get_or_create_homepage()
        index_page = SummerSchoolIndexPageFactory(parent=cls.page)
        cls.edition = SummerSchoolPageFactory(
            parent=index_page, featured=True, is_visible_on_homepage=True,
        )
        cls.application_page = SummerSchoolApplicationPageFactory(parent=cls.edition)

    def test_renders_with_open_application(self):
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.application_page.url)
        self.assertNotContains(response, "Applications closed")

    def test_renders_closed_state_after_deadline(self):
        self.application_page.application_deadline = timezone.now().date() - timedelta(days=1)
        self.application_page.save()

        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applications closed")
        self.assertNotContains(response, self.application_page.url)
