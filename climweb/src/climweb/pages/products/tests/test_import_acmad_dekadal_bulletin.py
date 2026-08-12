from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_dekadal_bulletin import (
    MAX_PDF_SIZE,
    canonical_source_url,
    history_document_from_dataset,
    infer_history_issue_date,
    iso_date,
    operational_url,
    parse_catalog,
    parse_thredds_catalog,
    versioned_source_url,
)
from climweb.pages.products.tasks import run_acmad_dekadal_import


class TestDekadalCatalogParsing(SimpleTestCase):
    catalog_url = "https://rcc.acmad.org/dacadebulletin.php"

    def test_parse_catalog_finds_bulletin_note_and_embedded_highlights(self):
        html = (
            """
            <a href="http://sgbd.acmad.org:8080/files/Bull_dek.pdf">Bulletin</a>
            <a href="http://sgbd.acmad.org:8080/files/Dek_Tech_Note.pdf">Note</a>
            <iframe src="https://docs.google.com/gview?url="""
            "http://sgbd.acmad.org:8080/files/HIGHLIHTS_DEKAD.pdf"
            """&amp;embedded=true"></iframe>
            """
        )

        documents = parse_catalog(html, self.catalog_url)

        self.assertEqual(
            [document["key"] for document in documents],
            ["bulletin", "technical-note", "highlights"],
        )
        self.assertTrue(all(
            document["source_url"].startswith("https://sgbd.acmad.org/")
            for document in documents
        ))

    def test_operational_and_canonical_urls_preserve_paths(self):
        source = "https://sgbd.acmad.org/thredds/fileServer/example.pdf"
        self.assertEqual(
            operational_url(source),
            "http://sgbd.acmad.org:8080/thredds/fileServer/example.pdf",
        )
        self.assertEqual(
            canonical_source_url(operational_url(source)),
            source,
        )

    def test_versioned_source_url_is_stable_per_issue(self):
        self.assertEqual(
            versioned_source_url("https://example.org/bulletin.pdf", date(2026, 3, 27)),
            "https://example.org/bulletin.pdf?acmad_issue=2026-03-27",
        )

    def test_iso_date_and_pdf_limit(self):
        self.assertEqual(iso_date("2026-03-27"), date(2026, 3, 27))
        self.assertEqual(MAX_PDF_SIZE, 50 * 1024 * 1024)

    def test_parse_thredds_catalog_returns_refs_and_file_datasets(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
                 xmlns:xlink="http://www.w3.org/1999/xlink">
          <dataset name="Dek1">
            <catalogRef xlink:href="Bulletin/catalog.xml" xlink:title="Bulletin" />
            <dataset name="Bull_dek1_Jan_2025.pdf"
                     urlPath="archive/2025/Jan/Dekad/Dek1/Bull/Bull_dek1_Jan_2025.pdf" />
          </dataset>
        </catalog>"""

        references, datasets = parse_thredds_catalog(
            xml,
            "https://sgbd.acmad.org/thredds/catalog/archive/catalog.xml",
        )

        self.assertEqual(references[0]["title"], "Bulletin")
        self.assertEqual(
            references[0]["catalog_url"],
            "https://sgbd.acmad.org/thredds/catalog/archive/Bulletin/catalog.xml",
        )
        self.assertEqual(datasets[0]["name"], "Bull_dek1_Jan_2025.pdf")
        self.assertIn("/thredds/fileServer/archive/2025/", datasets[0]["source_url"])

    def test_history_date_uses_dekad_end_and_filename_metadata(self):
        self.assertEqual(
            infer_history_issue_date(
                "https://example.org/2022/January/Dekad/Dek2/Bull_dek2_Jan_2022.pdf"
            ),
            date(2022, 1, 20),
        )
        self.assertEqual(
            infer_history_issue_date(
                "https://example.org/2022/February/Dekad/Dek3/Tech_Feb_2022_Dek3.pdf"
            ),
            date(2022, 2, 28),
        )
        self.assertEqual(
            infer_history_issue_date(
                "https://example.org/2022/January/Dekad/Dek1/Dek1_Jan_2021_Technical.pdf"
            ),
            date(2021, 1, 10),
        )

    def test_history_dataset_classifies_bulletin_and_rejects_maps(self):
        bulletin = history_document_from_dataset({
            "name": "Bull_dek2_Jan_2022.pdf",
            "source_url": (
                "https://sgbd.acmad.org/thredds/fileServer/archive/2022/"
                "January/Dekad/Dek2/Bull/Bull_dek2_Jan_2022.pdf"
            ),
        })

        self.assertEqual(bulletin["key"], "bulletin")
        self.assertEqual(bulletin["date"], date(2022, 1, 20))
        self.assertIsNone(history_document_from_dataset({
            "name": "rainfall.png",
            "source_url": "https://example.org/2022/January/Dekad/Dek2/rainfall.png",
        }))


class TestAutomaticDekadalImport(TestCase):
    @override_settings(ACMAD_DEKADAL_AUTO_IMPORT=True)
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_dekadal_import.run()

        call_command.assert_called_once_with(
            "import_acmad_dekadal_bulletin",
            continue_on_error=True,
        )

    @override_settings(ACMAD_DEKADAL_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_dekadal_import.run()

        call_command.assert_not_called()
