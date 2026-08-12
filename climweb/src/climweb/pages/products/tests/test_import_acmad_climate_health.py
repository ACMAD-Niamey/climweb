from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.pages.products.management.commands.import_acmad_climate_health import (
    MAX_FILE_SIZE,
    compact_date,
    parse_media_inventory,
)
from climweb.pages.products.tasks import run_acmad_climate_health_import


class TestClimateHealthSources(SimpleTestCase):
    def test_media_inventory_selects_only_audited_files(self):
        payload = [
            {
                "id": 4134,
                "date": "2022-10-27T06:01:43",
                "mime_type": "application/pdf",
                "slug": "meningitis_bulletin_20220324-2",
                "source_url": (
                    "http://acmad.org/wp-content/uploads/2019/03/"
                    "Meningitis_Bulletin_20220324-1.pdf"
                ),
            },
            {
                "id": 2816,
                "date": "2022-04-26T17:32:53",
                "mime_type": "application/pdf",
                "slug": "acmad_meningitis_bulletin_15_2022",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2019/03/"
                    "ACMAD_Meningitis_Bulletin_15_2022.pdf"
                ),
            },
            {
                "id": 12199,
                "date": "2024-04-26T19:10:43",
                "mime_type": "application/pdf",
                "slug": "acmad_meningitis-climenv-factors_tn_20240425",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2019/03/"
                    "ACMAD_Meningitis-ClimEnv-Factors_TN_20240425.pdf"
                ),
            },
            {
                "id": 12215,
                "date": "2024-04-29T11:33:29",
                "mime_type": "image/jpeg",
                "slug": "meningitis_bulletin",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2024/04/"
                    "Meningitis_Bulletin.jpg"
                ),
            },
            {
                "id": 12174,
                "date": "2024-04-25T17:04:14",
                "mime_type": "application/pdf",
                "slug": "draft-meningitis-vigilance-map-verification",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2019/03/"
                    "Draft-Meningitis-vigilance-map-verification.pdf"
                ),
            },
            {
                "id": 15718,
                "date": "2026-03-27T09:39:22",
                "mime_type": (
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                "slug": "meningitiskickoffmeeting_fi2026",
                "source_url": (
                    "https://acmad.org/wp-content/uploads/2019/03/"
                    "MeningitisKickoffMeeting_FI2026.pptx"
                ),
            },
        ]

        assets = parse_media_inventory(payload)

        self.assertEqual(len(assets), 4)
        self.assertEqual(
            {asset["key"] for asset in assets},
            {
                "weekly-meningitis-bulletin",
                "climate-health-technical-note",
                "relative-humidity-forecast",
            },
        )
        dated_bulletin = next(
            asset
            for asset in assets
            if "20220324" in asset["filename"]
        )
        self.assertEqual(dated_bulletin["date"], date(2022, 3, 24))
        self.assertTrue(dated_bulletin["source_url"].startswith("https://"))
        weekly_bulletin = next(
            asset
            for asset in assets
            if asset["filename"] == "ACMAD_Meningitis_Bulletin_15_2022.pdf"
        )
        self.assertEqual(weekly_bulletin["date"], date(2022, 4, 26))

    def test_known_health_images_use_product_issue_dates(self):
        payload = [
            {
                "id": 12222,
                "date": "2024-04-29T18:43:23",
                "mime_type": "image/jpeg",
                "slug": "meningitis_bulletin2",
                "source_url": "https://acmad.org/Meningitis_Bulletin2.jpg",
            },
            {
                "id": 13615,
                "date": "2024-11-01T09:49:38",
                "mime_type": "image/jpeg",
                "slug": (
                    "climate-and-health-monitoring-meningitis-and-heat-waves"
                ),
                "source_url": "https://acmad.org/Climate-and-Health.jpg",
            },
        ]

        assets = parse_media_inventory(payload)

        self.assertEqual(
            [(asset["key"], asset["date"]) for asset in assets],
            [
                ("meningitis-vigilance-outlook", date(2024, 4, 25)),
                ("meningitis-outlook-verification", date(2024, 4, 8)),
            ],
        )
        self.assertEqual(compact_date("20240425"), date(2024, 4, 25))
        self.assertEqual(MAX_FILE_SIZE, 50 * 1024 * 1024)


class TestAutomaticClimateHealthImport(TestCase):
    @override_settings(
        ACMAD_CLIMATE_HEALTH_AUTO_IMPORT=True,
        ACMAD_CLIMATE_HEALTH_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_climate_health_import.run()

        call_command.assert_called_once_with(
            "import_acmad_climate_health",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_CLIMATE_HEALTH_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_climate_health_import.run()

        call_command.assert_not_called()
