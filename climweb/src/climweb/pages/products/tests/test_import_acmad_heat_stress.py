from datetime import date
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_heat_stress import (
    MAX_IMAGE_SIZE,
    OBSERVED_TMAX_URL,
    Command,
    compact_date,
    parse_catalog_references,
    parse_issue_catalog,
)
from climweb.pages.products.tasks import run_acmad_heat_stress_import


class TestHeatStressSources(SimpleTestCase):
    def test_catalog_references_separate_issue_dates_and_years(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
          xmlns:xlink="http://www.w3.org/1999/xlink">
          <catalogRef xlink:title="20260807" xlink:href="20260807/catalog.xml" />
          <catalogRef xlink:title="2025" xlink:href="2025/catalog.xml" />
          <catalogRef xlink:title="current" xlink:href="current/catalog.xml" />
        </catalog>"""

        issues, years = parse_catalog_references(
            xml_content, "http://example.org/heatwave/catalog.xml"
        )

        self.assertEqual(
            issues,
            {
                date(2026, 8, 7): (
                    "http://example.org/heatwave/20260807/catalog.xml"
                )
            },
        )
        self.assertEqual(
            years, {2025: "http://example.org/heatwave/2025/catalog.xml"}
        )

    def test_issue_catalog_selects_only_audited_png_products(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="20260807">
            <dataset name="consecutive_2_hot_days_40C_20260807_20260812.png"
              urlPath="ACMAD/heatwave/20260807/consecutive_2_hot_days_40C_20260807_20260812.png">
              <date type="modified">2026-08-07T08:08:23Z</date>
            </dataset>
            <dataset name="heat_index_20260807_20260807.png"
              urlPath="ACMAD/heatwave/20260807/heat_index_20260807_20260807.png" />
            <dataset name="heat_index_20260807_20260812.png"
              urlPath="ACMAD/heatwave/20260807/heat_index_20260807_20260812.png" />
            <dataset name="consecutive_2_hot_days_48C_20260807_20260812.png"
              urlPath="ACMAD/heatwave/20260807/consecutive_2_hot_days_48C_20260807_20260812.png" />
            <dataset name="hot_days_40C_20260807_20260812.tif"
              urlPath="ACMAD/heatwave/20260807/hot_days_40C_20260807_20260812.tif" />
            <dataset name="2026080700_SRAD_20260811.png"
              urlPath="ACMAD/heatwave/20260807/2026080700_SRAD_20260811.png" />
          </dataset>
        </catalog>"""

        assets = parse_issue_catalog(xml_content, date(2026, 8, 7))

        self.assertEqual(
            [asset["key"] for asset in assets],
            [
                "consecutive-2-hot-days-40c",
                "heat-index-day-0",
                "heat-index-day-5",
            ],
        )
        self.assertEqual(assets[0]["valid_until"], date(2026, 8, 12))
        self.assertEqual(assets[0]["source_version"], "2026-08-07T08:08:23Z")
        self.assertTrue(assets[0]["source_url"].endswith(".png"))

    def test_compact_date_and_image_limit(self):
        self.assertEqual(compact_date("20260807"), date(2026, 8, 7))
        self.assertEqual(MAX_IMAGE_SIZE, 10 * 1024 * 1024)

    @patch(
        "climweb.pages.products.management.commands."
        "import_acmad_heat_stress.requests.head"
    )
    def test_observed_tmax_uses_last_modified_version(self, head):
        response = Mock()
        response.headers = {
            "Content-Type": "image/jpeg",
            "Last-Modified": "Sat, 13 Aug 2022 06:05:41 GMT",
        }
        response.raise_for_status.return_value = None
        head.return_value = response

        asset = Command._discover_observed_tmax()

        self.assertEqual(asset["date"], date(2022, 8, 13))
        self.assertEqual(asset["source_url"], OBSERVED_TMAX_URL)
        self.assertIn("acmad_version=", asset["provenance_url"])


class TestAutomaticHeatStressImport(TestCase):
    @override_settings(
        ACMAD_HEAT_STRESS_AUTO_IMPORT=True,
        ACMAD_HEAT_STRESS_IMPORT_LIMIT=2,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_heat_stress_import.run()

        call_command.assert_called_once_with(
            "import_acmad_heat_stress",
            limit=2,
            continue_on_error=True,
        )

    @override_settings(ACMAD_HEAT_STRESS_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_heat_stress_import.run()

        call_command.assert_not_called()
