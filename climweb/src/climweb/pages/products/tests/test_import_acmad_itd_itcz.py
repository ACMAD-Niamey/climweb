from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_itd_itcz import (
    MAX_FILE_SIZE,
    operational_url,
    parse_csag_dates,
    parse_thredds_catalog,
)
from climweb.pages.products.tasks import run_acmad_itd_itcz_import


class TestItdItczSources(SimpleTestCase):
    def test_thredds_catalog_selects_only_audited_pdf_and_images(self):
        xml_content = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="ITD_MEAN_POSITION">
            <dataset name="itd_mean_position.pdf"
              urlPath="FIT/ITD_MEAN_POSITION/itd_mean_position.pdf">
              <date type="modified">2026-08-04T09:54:34Z</date>
            </dataset>
            <dataset name="itd_mean_position_20260303.pdf"
              urlPath="FIT/ITD_MEAN_POSITION/itd_mean_position_20260303.pdf" />
            <dataset name="ITD_20230621_06.png"
              urlPath="FIT/ITD_MEAN_POSITION/ITD_20230621_06.png" />
            <dataset name="FIT20200117.gif"
              urlPath="FIT/ITD_MEAN_POSITION/FIT20200117.gif" />
            <dataset name="daily_bulletin.pdf"
              urlPath="FIT/ITD_MEAN_POSITION/daily_bulletin.pdf" />
            <dataset name="itd_mean_position.docx"
              urlPath="FIT/ITD_MEAN_POSITION/itd_mean_position.docx" />
          </dataset>
        </catalog>"""

        assets = parse_thredds_catalog(xml_content)

        self.assertEqual(len(assets), 4)
        self.assertEqual(
            [asset["date"] for asset in assets],
            [
                date(2026, 8, 4),
                date(2026, 3, 3),
                date(2023, 6, 21),
                date(2020, 1, 17),
            ],
        )
        self.assertTrue(assets[0]["is_current"])
        self.assertIn("acmad_version=", assets[0]["provenance_url"])
        self.assertFalse(assets[1]["is_current"])
        self.assertEqual(MAX_FILE_SIZE, 20 * 1024 * 1024)

    def test_csag_index_accepts_only_compact_date_directories(self):
        html = """
        <a href="20220328/">20220328</a>
        <a href="20220404/">20220404</a>
        <a href="20221301/">invalid</a>
        <a href="notes/">notes</a>
        """

        self.assertEqual(
            parse_csag_dates(html),
            {date(2022, 3, 28), date(2022, 4, 4)},
        )

    def test_acmad_https_urls_use_operational_thredds_port(self):
        self.assertEqual(
            operational_url(
                "https://sgbd.acmad.org/thredds/fileServer/FIT/example.pdf"
            ),
            "http://sgbd.acmad.org:8080/thredds/fileServer/FIT/example.pdf",
        )
        self.assertEqual(
            operational_url("https://web.csag.uct.ac.za/archive/"),
            "https://web.csag.uct.ac.za/archive/",
        )


class TestAutomaticItdItczImport(SimpleTestCase):
    @override_settings(
        ACMAD_ITD_ITCZ_AUTO_IMPORT=True,
        ACMAD_ITD_ITCZ_IMPORT_LIMIT=2,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_itd_itcz_import.run()

        call_command.assert_called_once_with(
            "import_acmad_itd_itcz",
            limit=2,
            continue_on_error=True,
        )

    @override_settings(ACMAD_ITD_ITCZ_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_itd_itcz_import.run()

        call_command.assert_not_called()
