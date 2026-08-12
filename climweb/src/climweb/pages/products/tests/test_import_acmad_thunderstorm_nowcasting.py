from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_thunderstorm_nowcasting import (
    MAX_IMAGE_SIZE,
    compact_datetime,
    operational_url,
    parse_current_catalog,
    parse_ir_archive_catalog,
    parse_references,
)
from climweb.pages.products.tasks import run_acmad_nowcasting_import


class TestNowcastingSources(SimpleTestCase):
    def test_current_catalog_selects_four_audited_jpegs(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="SATELLITE">
            <dataset name="IR_108.jpg" urlPath="FIT/SATELLITE/IR_108.jpg">
              <date type="modified">2026-08-08T07:30:21Z</date>
            </dataset>
            <dataset name="CC.jpg" urlPath="FIT/SATELLITE/CC.jpg">
              <date type="modified">2026-08-08T07:30:17Z</date>
            </dataset>
            <dataset name="CC_DNC.jpg" urlPath="FIT/SATELLITE/CC_DNC.jpg">
              <date type="modified">2026-08-08T07:30:34Z</date>
            </dataset>
            <dataset name="CC_AIRMASS.jpg" urlPath="FIT/SATELLITE/CC_AIRMASS.jpg">
              <date type="modified">2026-08-08T07:30:28Z</date>
            </dataset>
            <dataset name="CC__.jpg" urlPath="FIT/SATELLITE/CC__.jpg">
              <date type="modified">2019-06-21T21:26:58Z</date>
            </dataset>
            <dataset name="index.html" urlPath="RDT/index.html" />
            <dataset name="storm.geojson" urlPath="RDT/storm.geojson" />
          </dataset>
        </catalog>"""

        assets = parse_current_catalog(xml_content)

        self.assertEqual(
            {asset["key"] for asset in assets},
            {
                "infrared-108",
                "colour-composite",
                "day-night-cloud",
                "airmass-rgb",
            },
        )
        self.assertEqual(
            {asset["issue_time"] for asset in assets},
            {datetime(2026, 8, 8, 7, 15, tzinfo=timezone.utc)},
        )
        self.assertTrue(
            all("acmad_version=" in asset["provenance_url"] for asset in assets)
        )

    def test_ir_archive_entry_constructs_all_channel_urls(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="IR_108_202608">
            <dataset name="IR_108.20260808071500.jpg"
              urlPath="FIT/SATELLITE/IR_108/example.jpg" />
            <dataset name="README.txt" urlPath="README.txt" />
          </dataset>
        </catalog>"""

        assets = parse_ir_archive_catalog(xml_content)

        self.assertEqual(len(assets), 4)
        self.assertEqual(
            {asset["issue_time"] for asset in assets},
            {datetime(2026, 8, 8, 7, 15, tzinfo=timezone.utc)},
        )
        self.assertTrue(
            any(
                "CC_AIRMASS.20260808071500.jpg" in asset["source_url"]
                for asset in assets
            )
        )

    def test_reference_and_url_helpers(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
          xmlns:xlink="http://www.w3.org/1999/xlink">
          <catalogRef xlink:title="IR_108_2026"
            xlink:href="IR_108_2026/catalog.xml" />
        </catalog>"""
        catalog_url = "https://sgbd.acmad.org/thredds/catalog/IR/catalog.xml"

        self.assertEqual(
            parse_references(xml_content, catalog_url),
            [
                (
                    "IR_108_2026",
                    "https://sgbd.acmad.org/thredds/catalog/IR/"
                    "IR_108_2026/catalog.xml",
                )
            ],
        )
        self.assertEqual(
            operational_url(
                "https://sgbd.acmad.org/thredds/fileServer/FIT/image.jpg"
            ),
            "http://sgbd.acmad.org:8080/thredds/fileServer/FIT/image.jpg",
        )
        self.assertEqual(
            compact_datetime("20260808071500"),
            datetime(2026, 8, 8, 7, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(MAX_IMAGE_SIZE, 10 * 1024 * 1024)


class TestAutomaticNowcastingImport(TestCase):
    @override_settings(
        ACMAD_NOWCASTING_AUTO_IMPORT=True,
        ACMAD_NOWCASTING_IMPORT_LIMIT=2,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_nowcasting_import.run()

        call_command.assert_called_once_with(
            "import_acmad_thunderstorm_nowcasting",
            limit=2,
            continue_on_error=True,
        )

    @override_settings(ACMAD_NOWCASTING_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_nowcasting_import.run()

        call_command.assert_not_called()
