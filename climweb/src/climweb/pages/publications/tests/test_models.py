import wagtail_factories
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import PublicationsIndexPageFactory, PublicationPageFactory
from ..models import PublicationDocument


class TestPublicationPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.index_page = PublicationsIndexPageFactory(parent=home_page)
        
        cls.publication1_page = PublicationPageFactory(parent=cls.index_page)
        cls.publication2_page = PublicationPageFactory(parent=cls.index_page)
    
    def test_publication_index_page_render(self):
        self.assertPageIsRenderable(self.index_page)
    
    def test_publication_index_page_meta_tags(self):
        resp = self.client.get(self.index_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.index_page, meta_tags, request=resp.wsgi_request)
    
    def test_publication_page_render(self):
        self.assertPageIsRenderable(self.publication1_page)
        self.assertPageIsRenderable(self.publication2_page)
    
    def test_publication_pages_meta_tags(self):
        resp = self.client.get(self.publication1_page.get_url())
        
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.publication1_page, meta_tags, request=resp.wsgi_request)
        
        resp = self.client.get(self.publication2_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.publication2_page, meta_tags, request=resp.wsgi_request)

    def test_publication_supports_multiple_language_documents(self):
        self.publication1_page.document_language = "English"
        self.publication1_page.document.download_count = 2
        self.publication1_page.document.save()
        self.publication1_page.save()

        french_document = wagtail_factories.DocumentFactory(download_count=3)
        PublicationDocument.objects.create(
            publication=self.publication1_page,
            language="French",
            document=french_document,
        )

        card = self.publication1_page.card_props

        self.assertEqual(len(card["card_files"]), 2)
        self.assertEqual(card["card_files"][0]["language"], "English")
        self.assertEqual(card["card_files"][1]["language"], "French")
        self.assertEqual(card["card_downloads"], 5)
        self.assertEqual(self.publication1_page.total_download_count, 5)

        response = self.client.get(self.publication1_page.get_url())
        self.assertContains(response, "English")
        self.assertContains(response, "French")
