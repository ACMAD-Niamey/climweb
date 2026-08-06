from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_dekadal_bulletin import (
    MAX_PDF_SIZE,
    canonical_source_url,
    iso_date,
    operational_url,
    parse_catalog,
    versioned_source_url,
)
from climweb.pages.products.tasks import run_acmad_dekadal_import


class TestDekadalCatalogParsing(SimpleTestCase):
    catalog_url = "https://rcc.acmad.org/dacadebulletin.php"

    def test_parse_catalog_finds_bulletin_note_and_embedded_highlights(self):
        html = """
            <a href="http://sgbd.acmad.org:8080/files/Bull_dek.pdf">Bulletin</a>
            <a href="http://sgbd.acmad.org:8080/files/Dek_Tech_Note.pdf">Note</a>
            <iframe
              src="https://docs.google.com/gview?url=http://sgbd.acmad.org:8080/files/HIGHLIHTS_DEKAD.pdf&amp;embedded=true">
            </iframe>
        """

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


class TestAutomaticDekadalImport(SimpleTestCase):
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
