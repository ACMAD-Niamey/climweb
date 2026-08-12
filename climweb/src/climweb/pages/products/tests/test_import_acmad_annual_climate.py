from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands.import_acmad_annual_climate import (
    Command,
    parse_annual_report_links,
    select_preferred_reports,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_annual_climate_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestAnnualClimateSources(SimpleTestCase):
    def test_parser_accepts_reports_and_excludes_non_pdf_assets(self):
        html = """
        <a href="reports/ACMAD_State_of_Climate_2020.pdf">2020 report</a>
        <a href="reports/State_Of_Climate_2014_2018.pdf">Summary</a>
        <a href="maps/state-of-climate-2020.zip">Maps</a>
        <a href="reports/State_Of_Climate_ReportGuidelines_2023.pdf">Guide</a>
        """

        assets = parse_annual_report_links(html)

        self.assertEqual(len(assets), 2)
        self.assertEqual(assets[0]["date"], date(2020, 12, 31))
        self.assertEqual(assets[1]["key"], "multi-year-summary")

    def test_final_report_replaces_provisional_edition(self):
        provisional = {
            "key": "wmo-report",
            "year": 2022,
            "priority": 10,
            "source_url": "provisional.pdf",
        }
        final = {**provisional, "priority": 100, "source_url": "final.pdf"}

        selected = select_preferred_reports([provisional, final])

        self.assertEqual(selected, [final])

    def test_parser_ignores_text_from_malformed_nested_anchors(self):
        html = """
        <a href="WMO_STATE_OF_CLIMATE/2021/1290_Statement_2021_en.pdf">2021,
        <a href="Preliminary_State_of_Climate_JanOct_2020.pdf">2020,
        <a href="State_Climate_Africa_2014_2018_SUMMARY_28July2019.pdf">
        SUMMARY 2014-2018</a>
        """

        assets = parse_annual_report_links(html)

        self.assertEqual(
            [(asset["key"], asset["year"]) for asset in assets],
            [
                ("wmo-report", 2021),
                ("acmad-assessment", 2020),
                ("multi-year-summary", 2018),
            ],
        )

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["annual-climate"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticAnnualClimateImport(TestCase):
    @override_settings(
        ACMAD_ANNUAL_CLIMATE_AUTO_IMPORT=True,
        ACMAD_ANNUAL_CLIMATE_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_annual_climate_import.run()

        call_command.assert_called_once_with(
            "import_acmad_annual_climate",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_ANNUAL_CLIMATE_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_annual_climate_import.run()

        call_command.assert_not_called()


class TestAnnualClimateHierarchy(TestCase):
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
        self.assertEqual(product_page.title, "Annual State of the Climate Report")
        self.assertEqual(len(item_types), 3)
        self.assertEqual(
            ProductPage.objects.filter(service=rcc_service).live().count(), 1
        )
