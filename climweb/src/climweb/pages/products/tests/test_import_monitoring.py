from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from climweb.base.models import Product
from climweb.pages.products.import_monitoring import (
    build_import_monitor_rows,
    build_import_monitor_summary,
)
from climweb.pages.products.import_registry import (
    PRODUCT_IMPORTS,
    PRODUCT_IMPORTS_BY_KEY,
)
from climweb.pages.products.models import ProductImportRun, ProductSourceImport
from climweb.pages.products.tasks import run_manual_product_import


class TestProductImportRegistry(TestCase):
    def test_registry_covers_all_ten_importer_families(self):
        self.assertEqual(len(PRODUCT_IMPORTS), 10)
        self.assertEqual(
            set(PRODUCT_IMPORTS_BY_KEY),
            {
                "multihazard",
                "rainfall",
                "dekadal",
                "policy-briefs",
                "atmospheric-analysis",
                "heat-stress",
                "itd-itcz",
                "thunderstorm-nowcasting",
                "climate-health",
                "seasonal-forecasts",
            },
        )
        self.assertEqual(
            len(PRODUCT_IMPORTS_BY_KEY["seasonal-forecasts"]["product_names"]),
            5,
        )


class TestProductImportMonitoring(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Daily Rainfall Monitoring",
            variable_name="daily-rainfall-monitoring",
            temporal_resolution="daily",
        )
        ProductSourceImport.objects.create(
            product=cls.product,
            source_url="https://example.com/rainfall-20260808.jpg",
            source_system="ACMAD SGBD/THREDDS GSMaP",
            source_published_date=date(2026, 8, 8),
            checksum_sha256="a" * 64,
            status=ProductSourceImport.STATUS_IMPORTED,
        )
        ProductSourceImport.objects.create(
            product=cls.product,
            source_url="https://example.com/rainfall-20260809.jpg",
            source_system="ACMAD SGBD/THREDDS GSMaP",
            source_published_date=date(2026, 8, 9),
            checksum_sha256="",
            status=ProductSourceImport.STATUS_FAILED,
            error_message="Upstream source unavailable",
        )

    @override_settings(
        ACMAD_RAINFALL_AUTO_IMPORT=True,
        ACMAD_RAINFALL_IMPORT_INTERVAL_HOURS=6,
    )
    def test_monitoring_aggregates_provenance_and_health(self):
        rows = build_import_monitor_rows()
        rainfall = next(row for row in rows if row["key"] == "rainfall")

        self.assertTrue(rainfall["enabled"])
        self.assertEqual(rainfall["interval_hours"], 6)
        self.assertEqual(rainfall["imported_count"], 1)
        self.assertEqual(rainfall["failed_count"], 1)
        self.assertEqual(rainfall["latest_source_date"], date(2026, 8, 8))
        self.assertEqual(rainfall["health"], "attention")
        self.assertEqual(
            rainfall["latest_failure"].error_message,
            "Upstream source unavailable",
        )

        summary = build_import_monitor_summary(rows)
        self.assertEqual(summary["families"], 10)
        self.assertEqual(summary["imported"], 1)
        self.assertEqual(summary["failed"], 1)

    def test_admin_monitor_renders_all_importer_families(self):
        user = get_user_model().objects.create_superuser(
            username="import-admin",
            email="imports@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("product_import_monitor"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product Imports")
        self.assertContains(response, "Daily Rainfall Monitoring")
        self.assertContains(response, "Seasonal and Long-Range Forecasts")
        self.assertContains(response, "Upstream source unavailable")
        self.assertContains(response, "Manual historical import")

    @patch("climweb.pages.products.tasks.run_manual_product_import.delay")
    def test_admin_can_queue_historical_preview(self, delay):
        delay.return_value = SimpleNamespace(id="task-123")
        user = get_user_model().objects.create_superuser(
            username="historical-admin",
            email="history@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("product_import_monitor"),
            {
                "product_family": "seasonal-forecasts",
                "mode": "preview",
                "from_date": "2024-01-01",
                "to_date": "2024-12-31",
                "limit": 100,
            },
        )

        self.assertRedirects(response, reverse("product_import_monitor"))
        run = ProductImportRun.objects.get()
        self.assertEqual(run.product_family, "seasonal-forecasts")
        self.assertEqual(run.mode, ProductImportRun.MODE_PREVIEW)
        self.assertEqual(run.task_id, "task-123")
        self.assertEqual(run.requested_by, user)
        self.assertEqual(run.progress_percent, 0)
        delay.assert_called_once_with(run.pk)

    def test_progress_endpoint_reports_running_counters(self):
        user = get_user_model().objects.create_superuser(
            username="progress-admin",
            email="progress@example.com",
            password="test-password",
        )
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            status=ProductImportRun.STATUS_RUNNING,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            progress_percent=52,
            total_items=10,
            processed_items=5,
            imported_items=4,
            failed_items=1,
            current_phase="Processed 5 of 10 item(s)",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("product_import_status"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()["runs"][0]
        self.assertEqual(payload["id"], run.pk)
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["progress_percent"], 52)
        self.assertEqual(payload["processed_items"], 5)
        self.assertEqual(payload["failed_items"], 1)

    @patch("climweb.pages.products.tasks.call_command")
    def test_manual_import_tracks_real_provenance_progress(self, call_command):
        def simulate_import(command, stdout, **options):
            stdout.write("Selected 2 image(s).\n")
            ProductSourceImport.objects.create(
                product=self.product,
                source_url="https://example.com/progress-imported.jpg",
                source_system="Progress test",
                source_published_date=date(2026, 8, 10),
                checksum_sha256="b" * 64,
                status=ProductSourceImport.STATUS_IMPORTED,
            )
            stdout.write("SKIP 2026-08-09 already imported\n")

        call_command.side_effect = simulate_import
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            limit=10,
        )

        run_manual_product_import.run(run.pk)

        run.refresh_from_db()
        self.assertEqual(run.status, ProductImportRun.STATUS_SUCCEEDED)
        self.assertEqual(run.progress_percent, 100)
        self.assertEqual(run.total_items, 2)
        self.assertEqual(run.processed_items, 2)
        self.assertEqual(run.imported_items, 1)
        self.assertEqual(run.skipped_items, 1)
        self.assertEqual(run.current_phase, "Import completed")

    @patch("climweb.pages.products.tasks.call_command")
    def test_failed_manual_import_retains_partial_progress(self, call_command):
        def simulate_failure(command, stdout, **options):
            stdout.write("Selected 2 file(s).\n")
            ProductSourceImport.objects.create(
                product=self.product,
                source_url="https://example.com/progress-failed.jpg",
                source_system="Progress test",
                source_published_date=date(2026, 8, 10),
                checksum_sha256="",
                status=ProductSourceImport.STATUS_FAILED,
                error_message="Download failed",
            )
            raise CommandError("Import stopped")

        call_command.side_effect = simulate_failure
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            limit=10,
        )

        run_manual_product_import.run(run.pk)

        run.refresh_from_db()
        self.assertEqual(run.status, ProductImportRun.STATUS_FAILED)
        self.assertEqual(run.total_items, 2)
        self.assertEqual(run.processed_items, 1)
        self.assertEqual(run.failed_items, 1)
        self.assertEqual(run.progress_percent, 52)
        self.assertEqual(run.current_phase, "Import failed")
        self.assertEqual(run.error_message, "Import stopped")

    @patch("climweb.pages.products.tasks.call_command")
    def test_manual_runner_supports_every_registered_product_family(
        self,
        call_command,
    ):
        for definition in PRODUCT_IMPORTS:
            run = ProductImportRun.objects.create(
                product_family=definition["key"],
                mode=ProductImportRun.MODE_PREVIEW,
                from_date=date(2024, 1, 1),
                to_date=date(2024, 12, 31),
                limit=250,
                refresh_existing=True,
                retry_failures=True,
            )

            run_manual_product_import.run(run.pk)

            run.refresh_from_db()
            self.assertEqual(run.status, ProductImportRun.STATUS_SUCCEEDED)
            args, options = call_command.call_args
            self.assertEqual(args[0], definition["command"])
            self.assertEqual(options["from_date"], date(2024, 1, 1))
            self.assertEqual(options["to_date"], date(2024, 12, 31))
            self.assertEqual(options["limit"], 250)
            self.assertTrue(options["oldest_first"])
            self.assertTrue(options["continue_on_error"])
            self.assertTrue(options["dry_run"])
            self.assertTrue(options["refresh"])
            self.assertEqual(
                options.get("include_history", False),
                definition.get("include_history", False),
            )
            self.assertEqual(
                options.get("history_only", False),
                definition.get("history_only", False),
            )
            self.assertEqual(
                options.get("retry_failures", False),
                definition.get("supports_retry", False),
            )

        self.assertEqual(call_command.call_count, len(PRODUCT_IMPORTS))
