from types import SimpleNamespace

from django.test import SimpleTestCase

from climweb.base.templatetags.nmhs_cms_tags import public_page_url


class TestPublicPageUrl(SimpleTestCase):
    def test_removes_internal_home_page_slug(self):
        page = SimpleNamespace(
            url="/home-page/Services/climate-and-development-cdd/"
        )

        self.assertEqual(
            public_page_url(page),
            "/Services/climate-and-development-cdd/",
        )

    def test_maps_internal_home_page_to_public_root(self):
        self.assertEqual(public_page_url("/home-page/"), "/")

    def test_preserves_already_public_or_external_urls(self):
        self.assertEqual(public_page_url("/Services/cuip/"), "/Services/cuip/")
        self.assertEqual(public_page_url("https://example.com/page"), "https://example.com/page")
