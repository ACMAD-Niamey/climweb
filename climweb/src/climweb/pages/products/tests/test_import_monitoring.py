from datetime import date

from django.contrib.auth import get_user_model
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
from climweb.pages.products.models import ProductSourceImport


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
