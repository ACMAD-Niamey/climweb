from argparse import ArgumentTypeError
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_multihazard import (
    RANGE_CHUNK_SIZE,
    iso_date,
    operational_url,
    parse_archive,
    parse_year_archive_links,
)
from climweb.pages.products.tasks import (
    run_acmad_daily_rainfall_import,
    run_acmad_multihazard_import,
)


class TestMultiHazardArchiveParsing(SimpleTestCase):
    archive_url = (
        "https://sgbd.acmad.org/thredds/fileServer/FIT/BRIEFING/ARCHIVE/"
        "Hazard_Outlook/archive_hazard_outlook.html"
    )

    def test_operational_url_uses_working_sgbd_endpoint(self):
        source_url = "https://sgbd.acmad.org/thredds/fileServer/example.pdf"

        self.assertEqual(
            operational_url(source_url),
            "http://sgbd.acmad.org:8080/thredds/fileServer/example.pdf",
        )
        self.assertEqual(
            operational_url("https://example.org/example.pdf"),
            "https://example.org/example.pdf",
        )

    def test_parse_archive_deduplicates_and_sorts_dated_pdfs(self):
        html = """
            <a href="Continental_Hazard_Outlook_20260727.pdf">2026-07-27</a>
            <a href="Continental_Hazard_Outlook_20260730.pdf">2026-07-30</a>
            <a href="Continental_Hazard_Outlook_20260727.pdf">duplicate</a>
            <a href="archive_2025.html">2025</a>
            <a href="notes.txt">2026-07-31</a>
        """

        self.assertEqual(
            parse_archive(html, self.archive_url),
            [
                {
                    "date": date(2026, 7, 30),
                    "source_url": self._source_url(
                        "Continental_Hazard_Outlook_20260730.pdf"
                    ),
                },
                {
                    "date": date(2026, 7, 27),
                    "source_url": self._source_url(
                        "Continental_Hazard_Outlook_20260727.pdf"
                    ),
                },
            ],
        )

    def test_parse_year_archive_links_returns_only_unique_year_indexes(self):
        html = """
            <a href="archive_hazard_outlook_2025.html">2025</a>
            <a href="archive_hazard_outlook_2024.html">2024</a>
            <a href="archive_hazard_outlook_2025.html">duplicate</a>
            <a href="Continental_Hazard_Outlook_20250102.pdf">2025-01-02</a>
        """

        self.assertEqual(
            parse_year_archive_links(html, self.archive_url),
            [
                self._source_url("archive_hazard_outlook_2025.html"),
                self._source_url("archive_hazard_outlook_2024.html"),
            ],
        )

    def test_iso_date_rejects_invalid_values(self):
        self.assertEqual(iso_date("2026-07-30"), date(2026, 7, 30))
        with self.assertRaisesRegex(ArgumentTypeError, "Expected an ISO date"):
            iso_date("30-07-2026")

    def test_range_chunk_size_stays_within_pdf_size_limit(self):
        self.assertEqual(RANGE_CHUNK_SIZE, 8 * 1024 * 1024)
        self.assertLessEqual(RANGE_CHUNK_SIZE, 50 * 1024 * 1024)

    def _source_url(self, filename):
        return self.archive_url.rsplit("/", 1)[0] + "/" + filename


class TestAutomaticMultiHazardImport(SimpleTestCase):
    @override_settings(
        ACMAD_MULTIHAZARD_AUTO_IMPORT=True,
        ACMAD_MULTIHAZARD_IMPORT_LIMIT=12,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_idempotent_import_command(self, call_command):
        run_acmad_multihazard_import.run()

        call_command.assert_called_once_with(
            "import_acmad_multihazard",
            limit=12,
            continue_on_error=True,
        )

    @override_settings(ACMAD_MULTIHAZARD_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_does_not_run_import_command(self, call_command):
        run_acmad_multihazard_import.run()

        call_command.assert_not_called()


class TestAutomaticDailyRainfallImport(SimpleTestCase):
    @override_settings(
        ACMAD_RAINFALL_AUTO_IMPORT=True,
        ACMAD_RAINFALL_IMPORT_LIMIT=9,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_idempotent_import_command(self, call_command):
        run_acmad_daily_rainfall_import.run()

        call_command.assert_called_once_with(
            "import_acmad_daily_rainfall",
            limit=9,
            continue_on_error=True,
        )

    @override_settings(ACMAD_RAINFALL_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_does_not_run_import_command(self, call_command):
        run_acmad_daily_rainfall_import.run()

        call_command.assert_not_called()
