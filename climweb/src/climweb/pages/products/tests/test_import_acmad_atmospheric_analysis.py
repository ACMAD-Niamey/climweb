from datetime import date
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_atmospheric_analysis import (
    MAX_IMAGE_SIZE,
    SOURCE_SPECS,
    Command,
    iso_date,
    parse_history_issue_catalog,
    parse_history_root_catalog,
    versioned_source_url,
)
from climweb.pages.products.tasks import run_acmad_atmospheric_analysis_import


class TestAtmosphericAnalysisSources(SimpleTestCase):
    def test_default_pilot_has_eight_unique_healthy_source_specs(self):
        self.assertEqual(len(SOURCE_SPECS), 8)
        self.assertEqual(len({spec["key"] for spec in SOURCE_SPECS}), 8)
        self.assertTrue(
            all(spec["source_url"].endswith(".png") for spec in SOURCE_SPECS)
        )
        self.assertFalse(
            any(
                spec["filename"] == "ncep_climo_mslp_Africa_5days.png"
                for spec in SOURCE_SPECS
            )
        )
        self.assertEqual(
            {spec["category"] for spec in SOURCE_SPECS},
            {"5-day Atmospheric Climatology", "Daily Synoptic Analysis"},
        )

    @patch("climweb.pages.products.management.commands."
           "import_acmad_atmospheric_analysis.requests.head")
    def test_source_metadata_requires_png_and_returns_utc_version(self, head):
        response = Mock()
        response.headers = {
            "Content-Type": "image/png",
            "Last-Modified": "Fri, 07 Aug 2026 08:09:50 GMT",
        }
        response.raise_for_status.return_value = None
        head.return_value = response

        source_date, source_version = Command._source_metadata(
            "http://example.org/analysis.png"
        )

        self.assertEqual(source_date, date(2026, 8, 7))
        self.assertEqual(source_version, "2026-08-07T08:09:50+00:00")

    def test_date_versioning_and_image_limit(self):
        source = "http://example.org/analysis.png"
        self.assertEqual(
            versioned_source_url(source, "2026-08-07T08:09:50+00:00"),
            source + "?acmad_version=2026-08-07T08%3A09%3A50%2B00%3A00",
        )
        self.assertEqual(iso_date("2026-08-07"), date(2026, 8, 7))
        self.assertEqual(MAX_IMAGE_SIZE, 10 * 1024 * 1024)

    def test_history_root_catalog_returns_only_valid_dated_folders(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
          xmlns:xlink="http://www.w3.org/1999/xlink">
          <catalogRef xlink:title="current" xlink:href="current/catalog.xml" />
          <catalogRef xlink:title="20260806" xlink:href="20260806/catalog.xml" />
          <catalogRef xlink:title="20260230" xlink:href="bad/catalog.xml" />
        </catalog>"""

        catalogues = parse_history_root_catalog(
            xml_content, "http://example.org/archive/catalog.xml"
        )

        self.assertEqual(
            catalogues,
            {
                date(2026, 8, 6): (
                    "http://example.org/archive/20260806/catalog.xml"
                )
            },
        )

    def test_history_issue_catalog_selects_only_exact_pilot_files(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="folder">
            <dataset name="gfs_MSLP_Anom_Africa_init_D0-00_daily.png"
              urlPath="ACMAD/archive/20260806/gfs_MSLP_Anom_Africa_init_D0-00_daily.png">
              <date type="modified">2026-08-06T09:55:14Z</date>
            </dataset>
            <dataset name="wcm_gfs_MSLP_Anom_Africa_init_D0-00_daily.png"
              urlPath="ACMAD/archive/20260806/wcm_gfs_MSLP_Anom_Africa_init_D0-00_daily.png" />
            <dataset name="gfs_MSLP_Anom_Africa_init_D1-00_daily.png"
              urlPath="ACMAD/archive/20260806/gfs_MSLP_Anom_Africa_init_D1-00_daily.png" />
          </dataset>
        </catalog>"""
        specs = [
            spec for spec in SOURCE_SPECS if spec["key"] == "gfs-mslp-anomaly"
        ]

        assets = parse_history_issue_catalog(
            xml_content, date(2026, 8, 6), specs
        )

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["key"], "gfs-mslp-anomaly")
        self.assertEqual(assets[0]["date"], date(2026, 8, 6))
        self.assertEqual(assets[0]["source_version"], "2026-08-06T09:55:14Z")
        self.assertEqual(
            assets[0]["source_url"],
            "http://154.66.220.45:8080/thredds/fileServer/ACMAD/archive/"
            "20260806/gfs_MSLP_Anom_Africa_init_D0-00_daily.png",
        )


class TestAutomaticAtmosphericAnalysisImport(SimpleTestCase):
    @override_settings(ACMAD_ATMOSPHERIC_ANALYSIS_AUTO_IMPORT=True)
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_atmospheric_analysis_import.run()

        call_command.assert_called_once_with(
            "import_acmad_atmospheric_analysis",
            continue_on_error=True,
        )

    @override_settings(ACMAD_ATMOSPHERIC_ANALYSIS_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_atmospheric_analysis_import.run()

        call_command.assert_not_called()
