from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands import (
    import_acmad_model_performance as performance,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_model_performance_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestModelPerformanceSources(SimpleTestCase):
    def test_options_and_season_parsing(self):
        html = (
            b"<select><option>Cor_sst_CFS_JFM\n"
            b"<option>Feb-Mar-April_NMME\n</select>"
        )
        labels = performance.parse_options(html)
        self.assertEqual(labels, ["Cor_sst_CFS_JFM", "Feb-Mar-April_NMME"])
        self.assertEqual(performance.season_month(labels[0], 9), 1)
        self.assertEqual(performance.season_month(labels[1], 9), 2)

    def test_asset_builder_classifies_models_and_variables(self):
        static = performance.make_asset(
            "https://example.com/static.php",
            2017,
            "static",
            "hg",
            2,
            "Cor_sst_CFS_JFM",
        )
        dynamic = performance.make_asset(
            "https://example.com/dynamic.php",
            2014,
            "dynamic",
            "md",
            13,
            "Jan-Feb-Mar_NMME",
        )
        self.assertEqual(static["date"], date(2017, 1, 1))
        self.assertEqual(static["name"], "CFS")
        self.assertEqual(dynamic["name"], "Temperature — NMME")
        self.assertEqual(dynamic["category"], "Dynamical Model Skill Maps")

    def test_audited_inventory_contains_175_files(self):
        total = 48 + sum(len(files) for files in performance.STATIC_ARCHIVES.values())
        total += len(performance.DYNAMIC_FILES)
        self.assertEqual(total, 175)

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["model-performance"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticModelPerformanceImport(TestCase):
    @override_settings(
        ACMAD_MODEL_PERFORMANCE_AUTO_IMPORT=True,
        ACMAD_MODEL_PERFORMANCE_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_model_performance_import.run()
        call_command.assert_called_once_with(
            "import_acmad_model_performance",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_MODEL_PERFORMANCE_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_model_performance_import.run()
        call_command.assert_not_called()


class TestModelPerformanceHierarchy(TestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        ProductIndexPageFactory(parent=home_page)

    def test_destination_uses_rcc_service_and_two_categories(self):
        rcc_service = ServiceCategory.objects.create(
            name="Regional Climate Center", icon="cloud-sun-rain"
        )
        assets = [
            performance.make_asset(
                "https://example.com/static.php",
                2017,
                "static",
                "hg",
                1,
                "Cor_sst_CFS_JFM",
            ),
            performance.make_asset(
                "https://example.com/dynamic.php",
                2014,
                "dynamic",
                "hg",
                1,
                "Jan-Feb-Mar_NMME",
            ),
        ]
        destinations = performance.Command._get_or_create_destinations(assets)
        page = ProductPage.objects.get(slug="seasonal-model-performance")
        self.assertEqual(page.service, rcc_service)
        self.assertEqual(len(destinations), 2)
        self.assertEqual(page.product.categories.count(), 2)
