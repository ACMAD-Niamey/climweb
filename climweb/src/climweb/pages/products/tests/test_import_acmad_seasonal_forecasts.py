from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.management.commands.import_acmad_seasonal_forecasts import (
    Command,
    PRODUCT_DEFINITIONS,
    classify_asset,
    operational_url,
    parse_media_inventory,
    parse_thredds_catalog,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_seasonal_forecast_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestSeasonalForecastSources(SimpleTestCase):
    def test_media_inventory_selects_products_and_excludes_event_material(self):
        payload = [
            {
                "date": "2021-11-16T13:16:33",
                "mime_type": "application/pdf",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2019/03/"
                    "EN_SARCOF-25-STATEMENT.pdf"
                ),
            },
            {
                "date": "2021-11-16T13:17:59",
                "mime_type": "image/jpeg",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2019/03/"
                    "OND_2021_FCST_MAP_SARCOF_25.jpg"
                ),
            },
            {
                "date": "2024-09-11T18:18:53",
                "mime_type": "application/pdf",
                "source_url": "https://acmad.org/PRESAC-19-Agenda.pdf",
            },
            {
                "date": "2024-09-11T18:14:51",
                "mime_type": "image/jpeg",
                "source_url": "https://acmad.org/PRESAC_BANNER.jpeg",
            },
        ]

        assets = parse_media_inventory(payload)

        self.assertEqual(len(assets), 2)
        self.assertEqual(
            {asset["category"] for asset in assets},
            {"Consensus Statements and Communiqués", "Seasonal Forecast Maps"},
        )
        statement = next(asset for asset in assets if asset["kind"] == "document")
        forecast_map = next(asset for asset in assets if asset["kind"] == "image")
        self.assertEqual(statement["date"], date(2021, 11, 16))
        self.assertEqual(statement["key"], "sarcof-consensus-statement-english")
        self.assertEqual(forecast_map["key"], "sarcof-forecast-map-ond")

    def test_thredds_catalog_uses_modified_date_and_encodes_spaces(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="statement">
            <dataset name="Consensus Statement MedCOF21.pdf"
              urlPath="RCOF/MEDCOF/Consensus Statement MedCOF21.pdf">
              <date type="modified">2024-03-12T17:08:38Z</date>
            </dataset>
            <dataset name="Meeting Agenda.pdf" urlPath="RCOF/Meeting Agenda.pdf">
              <date type="modified">2024-03-12T17:08:38Z</date>
            </dataset>
          </dataset>
        </catalog>"""

        assets = parse_thredds_catalog(xml)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["date"], date(2024, 3, 12))
        self.assertEqual(assets[0]["key"], "medcof-consensus-statement")
        self.assertIn("Consensus%20Statement%20MedCOF21.pdf", assets[0]["source_url"])
        self.assertEqual(assets[0]["source_system"], "ACMAD THREDDS")

    def test_classifier_recognises_bilingual_and_seasonal_variants(self):
        french = classify_asset(
            "Communique-Finale_PRESAC-19_VF.pdf", "application/pdf"
        )
        map_asset = classify_asset(
            "PRECIP_FCST_MAM_PRESAGG_2024.jpg", "image/jpeg"
        )

        self.assertEqual(french["key"], "presac-consensus-statement-french")
        self.assertEqual(map_asset["key"], "presagg-forecast-map-mam")
        self.assertIsNone(
            classify_asset("PRESAC-19_TOPBANNER.jpg", "image/jpeg")
        )
        self.assertEqual(
            operational_url("https://sgbd.acmad.org/thredds/catalog/a.xml"),
            "http://sgbd.acmad.org:8080/thredds/catalog/a.xml",
        )


class TestAutomaticSeasonalForecastImport(TestCase):
    @override_settings(
        ACMAD_SEASONAL_FORECAST_AUTO_IMPORT=True,
        ACMAD_SEASONAL_FORECAST_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_seasonal_forecast_import.run()

        call_command.assert_called_once_with(
            "import_acmad_seasonal_forecasts",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_SEASONAL_FORECAST_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_seasonal_forecast_import.run()

        call_command.assert_not_called()


class TestSeasonalForecastHierarchy(TestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        ProductIndexPageFactory(parent=home_page)

    def test_destination_creates_service_category_and_five_product_pages(self):
        asset = {
            "key": "sarcof-forecast-map-ond",
            "name": "SARCOF Seasonal Forecast Map (OND)",
            "category": "Seasonal Forecast Maps",
            "kind": "image",
        }

        destinations = Command._get_or_create_destinations([asset])

        service = ServiceCategory.objects.get(name="Regional Climate Center")
        pages = ProductPage.objects.filter(service=service).live()
        self.assertEqual(pages.count(), 5)
        self.assertEqual(
            set(pages.values_list("title", flat=True)),
            set(PRODUCT_DEFINITIONS),
        )
        product_page, item_type = destinations[asset["key"]]
        self.assertEqual(product_page.title, "Seasonal Forecast Maps")
        self.assertEqual(item_type.category.product, product_page.product)
