from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.management.commands.import_acmad_monthly_climate import (
    Command,
    asset_from_dataset,
    issue_date_from_catalog_url,
    parse_catalog,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_monthly_climate_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestMonthlyClimateSources(SimpleTestCase):
    def test_catalog_parser_returns_references_and_datasets(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
                 xmlns:xlink="http://www.w3.org/1999/xlink">
          <dataset name="Monthly bulletin">
            <catalogRef xlink:href="2026/catalog.xml" xlink:title="2026" />
            <dataset name="Africa_rev_rfe_total_precip.png"
              urlPath="ACMAD/CDD/2026/Jul/Africa_rev_rfe_total_precip.png" />
          </dataset>
        </catalog>"""

        references, datasets = parse_catalog(
            xml, "https://sgbd.acmad.org/thredds/catalog/root/catalog.xml"
        )

        self.assertEqual(references[0]["title"], "2026")
        self.assertEqual(
            references[0]["catalog_url"],
            "https://sgbd.acmad.org/thredds/catalog/root/2026/catalog.xml",
        )
        self.assertEqual(datasets[0]["filename"], "Africa_rev_rfe_total_precip.png")

    def test_issue_date_and_asset_classification_use_catalog_month(self):
        catalog_url = (
            "https://sgbd.acmad.org/thredds/catalog/ACMAD/CDD/"
            "ClimateBulletin_TN/Monthly_Bulletin/2026/Jul/Rain_Review/"
            "spatial_maps/Africa/catalog.xml"
        )
        dataset = {
            "filename": "Africa_rev_rfe_total_precip.png",
            "source_path": "ACMAD/CDD/monthly/Africa_rev_rfe_total_precip.png",
        }

        asset = asset_from_dataset(dataset, catalog_url)

        self.assertEqual(issue_date_from_catalog_url(catalog_url), date(2026, 7, 1))
        self.assertEqual(asset["date"], date(2026, 7, 1))
        self.assertEqual(asset["valid_until"], date(2026, 7, 31))
        self.assertIn("/thredds/fileServer/ACMAD/CDD/", asset["source_url"])
        self.assertIsNone(asset_from_dataset({
            "filename": "Africa_climate_review_index.html",
            "source_path": "ACMAD/CDD/monthly/index.html",
        }, catalog_url))


class TestAutomaticMonthlyClimateImport(TestCase):
    @override_settings(
        ACMAD_MONTHLY_CLIMATE_AUTO_IMPORT=True,
        ACMAD_MONTHLY_CLIMATE_IMPORT_LIMIT=3,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_monthly_climate_import.run()

        call_command.assert_called_once_with(
            "import_acmad_monthly_climate",
            limit=3,
            continue_on_error=True,
        )

    @override_settings(ACMAD_MONTHLY_CLIMATE_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_monthly_climate_import.run()

        call_command.assert_not_called()


class TestMonthlyClimateHierarchy(TestCase):
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
        self.assertEqual(product_page.title, "Monthly Climate Diagnostic Bulletin")
        self.assertEqual(len(item_types), 12)
        self.assertEqual(
            ProductPage.objects.filter(service=rcc_service).live().count(), 1
        )
