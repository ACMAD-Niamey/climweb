from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import ServiceIndexPageFactory, ServicePageFactory


class TestServicesPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.index_page = ServiceIndexPageFactory(parent=home_page)
        cls.service1_page = ServicePageFactory(parent=cls.index_page)
        cls.service2_page = ServicePageFactory(parent=cls.index_page)
    
    def test_index_page_render(self):
        self.assertPageIsRenderable(self.index_page)
    
    def test_index_page_meta_tags(self):
        resp = self.client.get(self.index_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.index_page, meta_tags, request=resp.wsgi_request)
    
    def test_news_page_render(self):
        self.assertPageIsRenderable(self.service1_page)
        self.assertPageIsRenderable(self.service2_page)
    
    def test_news_page_meta_tags(self):
        resp = self.client.get(self.service1_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.service1_page, meta_tags, request=resp.wsgi_request)
        
        resp = self.client.get(self.service2_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.service2_page, meta_tags, request=resp.wsgi_request)

    def test_rcc_service_uses_dedicated_landing_page(self):
        rcc_page = ServicePageFactory(
            parent=self.index_page,
            title="Regional Climate Center",
            service__name="Regional Climate Center",
        )

        response = self.client.get(rcc_page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "services/rcc_service_page.html")
        self.assertContains(response, "Regional Climate Center products")
        self.assertContains(response, "Climate data services for Africa")

    def test_other_services_keep_default_template(self):
        response = self.client.get(self.service1_page.get_url())

        self.assertTemplateUsed(response, "services/service_page.html")
        self.assertTemplateNotUsed(response, "services/rcc_service_page.html")
