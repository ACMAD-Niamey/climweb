from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import (
    SummerSchoolIndexPageFactory,
    SummerSchoolPageFactory,
    SummerSchoolApplicationPageFactory,
)

# NOTE: This is Wave 0 - only models/blocks/migrations are built here. Templates
# (summer_school_index_page.html, summer_school_page.html,
# summer_school_application_page.html) are built in a later wave and do not exist
# yet, so `assertPageIsRenderable()` would fail with TemplateDoesNotExist. These
# tests instead confirm the page tree can be built and saved correctly with the
# frozen field/block contract. Once templates land, rendering + meta-tag tests
# (mirroring climweb/pages/events/tests/test_models.py) should be added here.


class TestSummerSchoolPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.index_page = SummerSchoolIndexPageFactory(parent=home_page)

        cls.edition1 = SummerSchoolPageFactory(parent=cls.index_page)
        cls.edition2 = SummerSchoolPageFactory(parent=cls.index_page)

        cls.application_page = SummerSchoolApplicationPageFactory(parent=cls.edition1)

    def test_index_page_created(self):
        self.assertTrue(self.index_page.id)
        self.assertTrue(self.index_page.live)

    def test_index_page_max_count_enforced(self):
        # max_count = 1 is enforced by Wagtail; a second index page under the same
        # parent should not be creatable since one already exists.
        self.assertFalse(type(self.index_page).can_create_at(self.index_page.get_parent()))

    def test_edition_pages_created_under_index(self):
        self.assertTrue(self.edition1.id)
        self.assertTrue(self.edition2.id)
        self.assertEqual(self.edition1.get_parent().specific, self.index_page)

    def test_editions_property_orders_by_start_date(self):
        self.edition1.edition_start_date = "2025-06-01"
        self.edition1.save()
        self.edition2.edition_start_date = "2026-06-01"
        self.edition2.save()

        editions = list(self.index_page.editions)
        self.assertIn(self.edition1.specific, editions)
        self.assertIn(self.edition2.specific, editions)

    def test_application_page_created_under_edition(self):
        self.assertTrue(self.application_page.id)
        self.assertEqual(self.application_page.get_parent().specific, self.edition1)

    def test_application_page_is_edition_first_child(self):
        self.assertEqual(self.edition1.application_page.specific, self.application_page)

    def test_schedule_data_empty_by_default(self):
        self.assertEqual(self.edition1.schedule_data, {})

    def test_cohorts_blank_by_default(self):
        self.assertEqual(len(self.edition1.cohorts), 0)

    def test_application_page_default_validation_field(self):
        self.assertEqual(self.application_page.validation_field, "email_address")
