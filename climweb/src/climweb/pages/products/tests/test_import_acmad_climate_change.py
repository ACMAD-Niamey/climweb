from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands.import_acmad_climate_change import (
    Command,
    header_date,
    parse_report_links,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_climate_change_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestClimateChangeSources(SimpleTestCase):
    def test_parser_selects_reports_and_excludes_interactive_application(self):
        html = """
        <a href="report/Rapport_diallo_ACMAD.pdf">Scenario report</a>
        <a href="document/Doukpolo_rapport_final.pdf">Risk report</a>
        <a href="CC_Services/climate_change_indexes.html">Indices</a>
        <a href="training/slides.pdf">Training</a>
        """

        assets = list(parse_report_links(html))

        self.assertEqual(len(assets), 2)
        self.assertEqual(
            {asset["key"] for asset in assets},
            {"model-scenario-report", "climate-risk-study"},
        )

    def test_last_modified_header_supplies_issue_date(self):
        self.assertEqual(
            header_date({"Last-Modified": "Fri, 28 Oct 2022 12:30:46 GMT"}),
            date(2022, 10, 28),
        )
        self.assertIsNone(header_date({}))

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["climate-change"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticClimateChangeImport(TestCase):
    @override_settings(
        ACMAD_CLIMATE_CHANGE_AUTO_IMPORT=True,
        ACMAD_CLIMATE_CHANGE_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_climate_change_import.run()

        call_command.assert_called_once_with(
            "import_acmad_climate_change",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_CLIMATE_CHANGE_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_climate_change_import.run()

        call_command.assert_not_called()


class TestClimateChangeHierarchy(TestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        ProductIndexPageFactory(parent=home_page)

    def test_destination_uses_existing_rcc_service(self):
        rcc_service = ServiceCategory.objects.create(
            name="Regional Climate Center", icon="cloud-sun-rain"
        )

        product_page, item_types = Command._get_or_create_destination()

        product_page.refresh_from_db()
        self.assertEqual(product_page.service, rcc_service)
        self.assertEqual(product_page.title, "Climate Change and Climate Projections")
        self.assertEqual(len(item_types), 2)
        self.assertEqual(
            ProductPage.objects.filter(service=rcc_service).live().count(), 1
        )
