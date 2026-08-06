from argparse import ArgumentTypeError
from datetime import date

from django.test import SimpleTestCase

from climweb.pages.products.management.commands.import_acmad_daily_rainfall import (
    MAX_IMAGE_SIZE,
    iso_date,
    operational_url,
    parse_archive,
    parse_year_archive_links,
)


class TestDailyRainfallArchiveParsing(SimpleTestCase):
    archive_url = (
        "https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/"
        "verificationservice/OBS/ARCHIVE/GSMAP/archive_gsmap.html"
    )

    def test_operational_url_uses_working_sgbd_endpoint(self):
        self.assertEqual(
            operational_url("https://sgbd.acmad.org/thredds/fileServer/image.png"),
            "http://sgbd.acmad.org:8080/thredds/fileServer/image.png",
        )
        self.assertEqual(
            operational_url("https://example.org/image.png"),
            "https://example.org/image.png",
        )

    def test_parse_archive_deduplicates_and_sorts_dated_pngs(self):
        html = """
            <a href="2026/gsmap24_20260804.png">2026-08-04</a>
            <a href="2026/gsmap24_20260805.png">2026-08-05</a>
            <a href="2026/gsmap24_20260804.png">duplicate</a>
            <a href="2026/gsmap_20260806.dat">not an image</a>
        """

        self.assertEqual(
            parse_archive(html, self.archive_url),
            [
                {
                    "date": date(2026, 8, 5),
                    "source_url": self._source_url("2026/gsmap24_20260805.png"),
                },
                {
                    "date": date(2026, 8, 4),
                    "source_url": self._source_url("2026/gsmap24_20260804.png"),
                },
            ],
        )

    def test_parse_year_archive_links_returns_only_year_indexes(self):
        html = """
            <a href="2025/archive_gsmap_2025.html">2025</a>
            <a href="2024/archive_gsmap_2024.html">2024</a>
            <a href="2025/archive_gsmap_2025.html">duplicate</a>
            <a href="2026/gsmap24_20260805.png">image</a>
        """

        self.assertEqual(
            parse_year_archive_links(html, self.archive_url),
            [
                self._source_url("2025/archive_gsmap_2025.html"),
                self._source_url("2024/archive_gsmap_2024.html"),
            ],
        )

    def test_iso_date_rejects_invalid_values(self):
        self.assertEqual(iso_date("2026-08-05"), date(2026, 8, 5))
        with self.assertRaisesRegex(ArgumentTypeError, "Expected an ISO date"):
            iso_date("05-08-2026")

    def test_image_size_limit_is_ten_mebibytes(self):
        self.assertEqual(MAX_IMAGE_SIZE, 10 * 1024 * 1024)

    def _source_url(self, filename):
        return self.archive_url.rsplit("/", 1)[0] + "/" + filename
