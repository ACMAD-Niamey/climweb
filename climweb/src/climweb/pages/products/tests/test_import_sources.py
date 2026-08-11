from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase

from climweb.pages.products.import_sources import (
    get_product_import_source_command_options,
    inspect_product_import_source,
)
from climweb.pages.products.models import ProductImportSourceConfig


class TestProductImportSourceInspection(TestCase):
    def _values(self, source_type, source_url, extensions, pattern, date_format):
        return {
            "source_type": source_type,
            "source_url": source_url,
            "source_system": "Test source",
            "allowed_extensions": extensions,
            "filename_pattern": pattern,
            "date_format": date_format,
            "history_url_pattern": "",
            "request_headers": {},
        }

    @patch("climweb.pages.products.import_sources._request")
    def test_inspects_html_archive(self, request):
        request.return_value = SimpleNamespace(
            text='<a href="brief_20260810.pdf">Bulletin</a>'
        )
        values = self._values(
            "html_archive",
            "https://data.example.com/archive/",
            [".pdf"],
            r"brief_(?P<date>20\d{6})\.pdf$",
            "%Y%m%d",
        )

        result = inspect_product_import_source("multihazard", values)

        self.assertEqual(result["discovered_count"], 1)
        self.assertEqual(
            result["issues"][0]["source_url"],
            "https://data.example.com/archive/brief_20260810.pdf",
        )

    @patch("climweb.pages.products.import_sources._request")
    def test_inspects_thredds_catalogue_using_modified_date_fallback(self, request):
        request.return_value = SimpleNamespace(
            content=b"""<catalog
                xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
                <dataset name="policy.pdf" urlPath="briefs/policy.pdf">
                    <date type="modified">2026-08-09T12:00:00Z</date>
                </dataset>
            </catalog>"""
        )
        values = self._values(
            "thredds_catalog",
            "https://data.example.com/thredds/catalog/briefs/catalog.xml",
            [".pdf"],
            r"(?P<date>20\d{6})",
            "%Y%m%d",
        )

        result = inspect_product_import_source("policy-briefs", values)

        self.assertEqual(result["discovered_count"], 1)
        self.assertEqual(str(result["issues"][0]["date"]), "2026-08-09")

    @patch("climweb.pages.products.import_sources._request")
    def test_inspects_wordpress_media_api(self, request):
        response = Mock()
        response.json.return_value = [
            {
                "source_url": "https://data.example.com/media/outlook.pdf",
                "date_gmt": "2026-08-08T09:30:00",
            }
        ]
        request.return_value = response
        values = self._values(
            "wordpress_api",
            "https://data.example.com/wp-json/wp/v2/media",
            [".pdf"],
            r"(?P<date>20\d{6})",
            "%Y%m%d",
        )

        result = inspect_product_import_source("climate-health", values)

        self.assertEqual(result["discovered_count"], 1)
        self.assertEqual(str(result["issues"][0]["date"]), "2026-08-08")


class TestProductImportSourceCommandOptions(TestCase):
    def test_returns_empty_options_until_override_is_saved(self):
        self.assertEqual(
            get_product_import_source_command_options("policy-briefs"), {}
        )

    def test_adapts_single_url_to_repeatable_command_option(self):
        ProductImportSourceConfig.objects.create(
            product_family="seasonal-forecasts",
            source_type="wordpress_api",
            source_url="https://data.example.com/wp-json/wp/v2/media?search=seasonal",
            source_system="Example Seasonal API",
            allowed_extensions=[".pdf"],
            filename_pattern=r"(?P<date>20\d{6})",
            date_format="%Y%m%d",
        )

        self.assertEqual(
            get_product_import_source_command_options("seasonal-forecasts"),
            {
                "api_url": [
                    "https://data.example.com/wp-json/wp/v2/media?search=seasonal"
                ]
            },
        )
