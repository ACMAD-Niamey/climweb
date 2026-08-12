from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from climweb.base.models import Product
from climweb.pages.products.import_monitoring import (
    build_import_monitor_rows,
    build_import_monitor_summary,
)
from climweb.pages.products.import_registry import (
    PRODUCT_IMPORTS,
    PRODUCT_IMPORTS_BY_KEY,
)
from climweb.pages.products.models import (
    ProductImportRun,
    ProductImportSchedule,
    ProductImportSourceConfig,
    ProductSourceImport,
)
from climweb.pages.products.tasks import run_manual_product_import


class TestProductImportRegistry(TestCase):
    def test_registry_covers_all_eleven_importer_families(self):
        self.assertEqual(len(PRODUCT_IMPORTS), 11)
        self.assertEqual(
            set(PRODUCT_IMPORTS_BY_KEY),
            {
                "multihazard",
                "rainfall",
                "dekadal",
                "monthly-climate",
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
        self.assertTrue(
            all(
                definition.get("configurable_source")
                for definition in PRODUCT_IMPORTS
            )
        )
        self.assertEqual(
            {
                definition["source_defaults"]["source_type"]
                for definition in PRODUCT_IMPORTS
            },
            {"html_archive", "thredds_catalog", "wordpress_api"},
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
        self.assertEqual(summary["families"], 11)
        self.assertEqual(summary["imported"], 1)
        self.assertEqual(summary["failed"], 1)

    @override_settings(ACMAD_RAINFALL_IMPORT_INTERVAL_HOURS=6)
    def test_monitoring_uses_saved_interval_instead_of_default(self):
        ProductImportSchedule.objects.create(
            product_family="rainfall",
            interval_hours=12,
        )

        rows = build_import_monitor_rows()
        rainfall = next(row for row in rows if row["key"] == "rainfall")

        self.assertEqual(rainfall["interval_hours"], 12)
        self.assertTrue(rainfall["interval_is_custom"])

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
        self.assertContains(response, "Manage imports", count=11)
        self.assertNotContains(response, "Manual historical import")

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
            reverse(
                "product_import_family",
                kwargs={"family_key": "seasonal-forecasts"},
            ),
            {
                "mode": "preview",
                "from_date": "2024-01-01",
                "to_date": "2024-12-31",
                "limit": 100,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "product_import_family",
                kwargs={"family_key": "seasonal-forecasts"},
            ),
        )
        run = ProductImportRun.objects.get()
        self.assertEqual(run.product_family, "seasonal-forecasts")
        self.assertEqual(run.mode, ProductImportRun.MODE_PREVIEW)
        self.assertEqual(run.task_id, "task-123")
        self.assertEqual(run.requested_by, user)
        self.assertEqual(run.progress_percent, 0)
        delay.assert_called_once_with(run.pk)

    def test_family_page_scopes_history_and_renders_output_modal(self):
        user = get_user_model().objects.create_superuser(
            username="family-admin",
            email="family@example.com",
            password="test-password",
        )
        rainfall_run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_PREVIEW,
            status=ProductImportRun.STATUS_SUCCEEDED,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            progress_percent=100,
            current_phase="Import completed",
            output="Rainfall preview output",
        )
        ProductImportRun.objects.create(
            product_family="seasonal-forecasts",
            mode=ProductImportRun.MODE_PREVIEW,
            status=ProductImportRun.STATUS_SUCCEEDED,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 3, 1),
            output="Seasonal output must not appear",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daily Rainfall Monitoring")
        self.assertContains(response, "Manual historical import")
        self.assertContains(response, "Recent import history")
        self.assertContains(response, "Rainfall preview output")
        self.assertNotContains(response, "Seasonal output must not appear")
        self.assertContains(response, 'id="import-output-modal"')
        self.assertContains(
            response,
            f'data-output-source="run-output-{rainfall_run.pk}"',
        )
        self.assertContains(response, "View output")
        self.assertContains(response, "Automatic import schedule")
        self.assertContains(response, "Save schedule")

    def test_family_page_renders_stop_button_for_active_manual_import(self):
        user = get_user_model().objects.create_superuser(
            username="stop-button-admin",
            email="stop-button@example.com",
            password="test-password",
        )
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            status=ProductImportRun.STATUS_RUNNING,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            )
        )

        self.assertContains(response, "Stop import")
        self.assertContains(response, 'name="run_id" value="%s"' % run.pk)
        self.assertContains(response, "data-stop-import-form")

    @patch("climweb.config.celery.app.control.revoke")
    def test_admin_can_stop_queued_manual_import(self, revoke):
        user = get_user_model().objects.create_superuser(
            username="stop-queued-admin",
            email="stop-queued@example.com",
            password="test-password",
        )
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            status=ProductImportRun.STATUS_QUEUED,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            task_id="queued-task-123",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {"action": "cancel_import", "run_id": run.pk},
        )

        self.assertRedirects(
            response,
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
        )
        run.refresh_from_db()
        self.assertTrue(run.cancel_requested)
        self.assertEqual(run.status, ProductImportRun.STATUS_CANCELLED)
        self.assertEqual(run.current_phase, "Stopped before starting")
        self.assertIsNotNone(run.finished_at)
        revoke.assert_called_once_with("queued-task-123", terminate=False)

    @patch("climweb.config.celery.app.control.revoke")
    def test_admin_can_request_running_manual_import_to_stop(self, revoke):
        user = get_user_model().objects.create_superuser(
            username="stop-running-admin",
            email="stop-running@example.com",
            password="test-password",
        )
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            status=ProductImportRun.STATUS_RUNNING,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            task_id="running-task-123",
        )
        self.client.force_login(user)

        self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {"action": "cancel_import", "run_id": run.pk},
        )

        run.refresh_from_db()
        self.assertTrue(run.cancel_requested)
        self.assertEqual(run.status, ProductImportRun.STATUS_CANCELLING)
        self.assertEqual(run.current_phase, "Stop requested")
        self.assertIsNone(run.finished_at)
        revoke.assert_called_once_with("running-task-123", terminate=False)

    def test_rainfall_page_renders_source_schema_configuration(self):
        user = get_user_model().objects.create_superuser(
            username="source-admin",
            email="source@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Source and schema configuration")
        self.assertContains(response, "Test connection")
        self.assertContains(response, "Preview discovered files")
        self.assertContains(response, "archive_gsmap.html")

    def test_admin_can_save_rainfall_source_configuration(self):
        user = get_user_model().objects.create_superuser(
            username="save-source-admin",
            email="save-source@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {
                "action": "save_source",
                "source_type": "html_archive",
                "source_url": "https://data.example.com/rainfall/index.html",
                "source_system": "Example Rainfall Archive",
                "allowed_extensions": ".png, .jpg",
                "filename_pattern": r"rain_(?P<date>20\d{6})\.(png|jpg)$",
                "date_format": "%Y%m%d",
                "history_url_pattern": r"archive_20\d{2}\.html$",
                "request_headers": '{"Accept": "text/html"}',
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
        )
        config = ProductImportSourceConfig.objects.get(product_family="rainfall")
        self.assertEqual(config.source_url, "https://data.example.com/rainfall/index.html")
        self.assertEqual(config.allowed_extensions, [".png", ".jpg"])
        self.assertEqual(config.request_headers, {"Accept": "text/html"})
        self.assertEqual(config.updated_by, user)

        saved_response = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            )
        )
        self.assertContains(
            saved_response, "https://data.example.com/rainfall/index.html"
        )
        self.assertContains(saved_response, "Restore default configuration")

    def test_admin_can_restore_default_rainfall_source_configuration(self):
        user = get_user_model().objects.create_superuser(
            username="restore-source-admin",
            email="restore-source@example.com",
            password="test-password",
        )
        ProductImportSourceConfig.objects.create(
            product_family="rainfall",
            source_type="html_archive",
            source_url="https://tampered.example.com/index.html",
            source_system="Changed source",
            allowed_extensions=[".jpg"],
            filename_pattern=r"changed_(?P<date>20\d{6})\.jpg$",
            date_format="%Y%m%d",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {"action": "restore_source_defaults"},
        )

        self.assertRedirects(
            response,
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
        )
        self.assertFalse(ProductImportSourceConfig.objects.exists())
        restored_response = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            )
        )
        self.assertContains(restored_response, "archive_gsmap.html")
        self.assertNotContains(restored_response, "tampered.example.com")

    @patch("climweb.pages.products.import_sources.inspect_product_import_source")
    def test_admin_can_preview_rainfall_source_without_saving(self, inspect_source):
        inspect_source.return_value = {
            "archive_count": 1,
            "discovered_count": 1,
            "issues": [
                {
                    "date": date(2026, 8, 10),
                    "source_url": "https://data.example.com/rain_20260810.png",
                }
            ],
        }
        user = get_user_model().objects.create_superuser(
            username="preview-source-admin",
            email="preview-source@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {
                "action": "preview_source",
                "source_type": "html_archive",
                "source_url": "https://data.example.com/rainfall/index.html",
                "source_system": "Example Rainfall Archive",
                "allowed_extensions": ".png",
                "filename_pattern": r"rain_(?P<date>20\d{6})\.png$",
                "date_format": "%Y%m%d",
                "history_url_pattern": "",
                "request_headers": "{}",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Discovery preview")
        self.assertContains(response, "rain_20260810.png")
        self.assertFalse(ProductImportSourceConfig.objects.exists())
        inspect_source.assert_called_once()

    @override_settings(ACMAD_RAINFALL_AUTO_IMPORT=True)
    def test_admin_can_update_family_automatic_import_interval(self):
        user = get_user_model().objects.create_superuser(
            username="schedule-admin",
            email="schedule@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {
                "action": "update_schedule",
                "interval_hours": 12,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
        )
        schedule = ProductImportSchedule.objects.get(product_family="rainfall")
        self.assertEqual(schedule.interval_hours, 12)
        self.assertEqual(schedule.updated_by, user)
        periodic_task = PeriodicTask.objects.get(
            name="import-acmad-daily-rainfall-automatically"
        )
        self.assertEqual(
            periodic_task.task,
            "climweb.pages.products.tasks.run_acmad_daily_rainfall_import",
        )
        self.assertEqual(periodic_task.interval.every, 12)
        self.assertEqual(periodic_task.interval.period, IntervalSchedule.HOURS)
        self.assertTrue(periodic_task.enabled)

    @override_settings(ACMAD_RAINFALL_AUTO_IMPORT=True)
    def test_admin_can_disable_family_automatic_importer(self):
        user = get_user_model().objects.create_superuser(
            username="disable-importer-admin",
            email="disable-importer@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {"action": "disable_importer"},
        )

        self.assertRedirects(
            response,
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
        )
        schedule = ProductImportSchedule.objects.get(product_family="rainfall")
        self.assertFalse(schedule.enabled_override)
        self.assertEqual(schedule.updated_by, user)
        periodic_task = PeriodicTask.objects.get(
            name="import-acmad-daily-rainfall-automatically"
        )
        self.assertFalse(periodic_task.enabled)
        page = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            )
        )
        self.assertContains(page, "Enable importer")
        self.assertContains(page, "Dashboard override")

    def test_invalid_interval_is_shown_without_changing_schedule(self):
        user = get_user_model().objects.create_superuser(
            username="invalid-schedule-admin",
            email="invalid-schedule@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "product_import_family",
                kwargs={"family_key": "rainfall"},
            ),
            {
                "action": "update_schedule",
                "interval_hours": 0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value is greater than or equal to 1")
        self.assertFalse(
            ProductImportSchedule.objects.filter(product_family="rainfall").exists()
        )

    def test_every_registered_family_has_an_individual_import_page(self):
        user = get_user_model().objects.create_superuser(
            username="all-family-admin",
            email="all-families@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        for definition in PRODUCT_IMPORTS:
            with self.subTest(family=definition["key"]):
                response = self.client.get(
                    reverse(
                        "product_import_family",
                        kwargs={"family_key": definition["key"]},
                    )
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, definition["label"])
                self.assertContains(response, "Manual historical import")
                self.assertContains(response, "Automatic import schedule")
                self.assertContains(response, "importer")
                self.assertContains(response, "Source and schema configuration")
                self.assertContains(
                    response,
                    definition["source_defaults"]["source_url"].split("?", 1)[0],
                )
                self.assertContains(response, "Recent import history")

    def test_unknown_family_page_returns_404(self):
        user = get_user_model().objects.create_superuser(
            username="unknown-admin",
            email="unknown@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "product_import_family",
                kwargs={"family_key": "not-a-product"},
            )
        )

        self.assertEqual(response.status_code, 404)

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

        ProductImportRun.objects.create(
            product_family="seasonal-forecasts",
            mode=ProductImportRun.MODE_IMPORT,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 2, 1),
        )

        response = self.client.get(
            reverse(
                "product_import_family_status",
                kwargs={"family_key": "rainfall"},
            )
        )

        self.assertEqual(response.status_code, 200)
        runs = response.json()["runs"]
        self.assertEqual(len(runs), 1)
        payload = runs[0]
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
    def test_running_manual_import_stops_at_progress_checkpoint(self, call_command):
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            limit=10,
        )

        def request_stop(command, stdout, **options):
            ProductImportRun.objects.filter(pk=run.pk).update(
                cancel_requested=True,
                status=ProductImportRun.STATUS_CANCELLING,
            )
            stdout.write("Selected 10 image(s).\n")

        call_command.side_effect = request_stop

        run_manual_product_import.run(run.pk)

        run.refresh_from_db()
        self.assertEqual(run.status, ProductImportRun.STATUS_CANCELLED)
        self.assertTrue(run.cancel_requested)
        self.assertEqual(run.current_phase, "Stopped by user")
        self.assertIsNotNone(run.finished_at)

    @patch("climweb.pages.products.tasks.call_command")
    def test_cancelled_queued_import_never_starts(self, call_command):
        run = ProductImportRun.objects.create(
            product_family="rainfall",
            mode=ProductImportRun.MODE_IMPORT,
            status=ProductImportRun.STATUS_CANCELLED,
            cancel_requested=True,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 10),
            limit=10,
        )

        run_manual_product_import.run(run.pk)

        run.refresh_from_db()
        self.assertEqual(run.status, ProductImportRun.STATUS_CANCELLED)
        call_command.assert_not_called()

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

    @patch("climweb.pages.products.tasks.call_command")
    def test_manual_runner_passes_saved_source_override_to_importer(
        self, call_command
    ):
        ProductImportSourceConfig.objects.create(
            product_family="policy-briefs",
            source_type="thredds_catalog",
            source_url="https://data.example.com/policy/catalog.xml",
            source_system="Example Policy Catalogue",
            allowed_extensions=[".pdf"],
            filename_pattern=r"(?P<date>20\d{6})",
            date_format="%Y%m%d",
        )
        run = ProductImportRun.objects.create(
            product_family="policy-briefs",
            mode=ProductImportRun.MODE_PREVIEW,
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31),
            limit=10,
        )

        run_manual_product_import.run(run.pk)

        _, options = call_command.call_args
        self.assertEqual(
            options["catalog_url"],
            "https://data.example.com/policy/catalog.xml",
        )
