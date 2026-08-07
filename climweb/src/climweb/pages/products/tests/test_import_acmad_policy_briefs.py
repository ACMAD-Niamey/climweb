from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_policy_briefs import (
    MAX_IMAGE_SIZE,
    MAX_PDF_SIZE,
    canonical_source_url,
    classify_policy_asset,
    iso_date,
    operational_url,
    parse_thredds_catalog,
    versioned_source_url,
)
from climweb.pages.products.tasks import run_acmad_policy_briefs_import


class TestPolicyBriefCatalogParsing(SimpleTestCase):
    def test_catalog_whitelists_policy_brief_documents_and_images(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="Doc_Web">
            <dataset name="LRF_Policy_Brief.pdf"
                     urlPath="services/Doc_Web/LRF_Policy_Brief.pdf">
              <date type="modified">2026-05-29T09:18:20Z</date>
            </dataset>
            <dataset name="policy-breif.jpeg"
                     urlPath="services/Doc_Web/policy-breif.jpeg">
              <date type="modified">2025-12-12T22:06:56Z</date>
            </dataset>
            <dataset name="LRF_Policy_Brief5.png"
                     urlPath="services/Doc_Web/LRF_Policy_Brief5.png">
              <date type="modified">2023-06-16T12:13:08Z</date>
            </dataset>
            <dataset name="Dek_Tech_Note.pdf"
                     urlPath="services/Doc_Web/Dek_Tech_Note.pdf">
              <date type="modified">2026-03-27T18:29:44Z</date>
            </dataset>
          </dataset>
        </catalog>"""

        assets = parse_thredds_catalog(
            xml, "https://sgbd.acmad.org/thredds/catalog/Doc_Web/catalog.xml"
        )

        self.assertEqual(len(assets), 3)
        self.assertEqual(
            {asset["media_kind"] for asset in assets}, {"document", "image"}
        )
        self.assertEqual(assets[0]["date"], date(2026, 5, 29))
        self.assertTrue(
            all("/thredds/fileServer/services/Doc_Web/" in asset["source_url"] for asset in assets)
        )

    def test_classification_rejects_unrelated_shared_catalog_files(self):
        self.assertEqual(classify_policy_asset("LRF_Policy_Brief.pdf"), "document")
        self.assertEqual(classify_policy_asset("LRF_Policy_Brief.png"), "image")
        self.assertEqual(classify_policy_asset("policy-breif.jpeg"), "image")
        self.assertIsNone(classify_policy_asset("Long_Range_Forecast_Bulletin.pdf"))
        self.assertIsNone(classify_policy_asset("policy-brief.exe"))

    def test_operational_versioned_urls_and_limits(self):
        source = (
            "https://sgbd.acmad.org/thredds/fileServer/Doc_Web/"
            "LRF_Policy_Brief.png"
        )
        self.assertEqual(
            operational_url(source),
            "http://sgbd.acmad.org:8080/thredds/fileServer/Doc_Web/"
            "LRF_Policy_Brief.png",
        )
        self.assertEqual(canonical_source_url(operational_url(source)), source)
        self.assertEqual(
            versioned_source_url(source, "2026-05-29T09:18:20Z"),
            source + "?acmad_version=2026-05-29T09%3A18%3A20Z",
        )
        self.assertEqual(iso_date("2026-05-29"), date(2026, 5, 29))
        self.assertEqual(MAX_IMAGE_SIZE, 10 * 1024 * 1024)
        self.assertEqual(MAX_PDF_SIZE, 50 * 1024 * 1024)


class TestAutomaticPolicyBriefImport(SimpleTestCase):
    @override_settings(
        ACMAD_POLICY_BRIEFS_AUTO_IMPORT=True,
        ACMAD_POLICY_BRIEFS_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_policy_briefs_import.run()

        call_command.assert_called_once_with(
            "import_acmad_policy_briefs",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(
        ACMAD_POLICY_BRIEFS_AUTO_IMPORT=False,
        ACMAD_POLICY_BRIEFS_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_policy_briefs_import.run()

        call_command.assert_not_called()
