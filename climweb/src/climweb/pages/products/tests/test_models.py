import wagtail_factories
from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import ProductIndexPageFactory, ProductPageFactory, ProductItemPageFactory


class TestProductPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        
        cls.index_page = ProductIndexPageFactory(parent=home_page)
        cls.product1_page = ProductPageFactory(parent=cls.index_page)
        cls.product2_page = ProductPageFactory(parent=cls.index_page)
        
        product1_page_product_types = cls.product1_page.product.product_item_types
        
        cls.product1_page_product_item_page = ProductItemPageFactory(
            parent=cls.product1_page,
            products__0__image_product__product_type=product1_page_product_types[0][0],
            products__0__image_product__date=timezone.now().date(),
            products__1__document_product__product_type=product1_page_product_types[1][0],
            products__1__document_product__date=timezone.now().date(),
        )
    
    def test_products_index_page_render(self):
        self.assertPageIsRenderable(self.index_page)
    
    def test_products_index_page_meta_tags(self):
        resp = self.client.get(self.index_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.index_page, meta_tags, request=resp.wsgi_request)
    
    def test_product_page_render(self):
        self.assertPageIsRenderable(self.product1_page)
        self.assertPageIsRenderable(self.product2_page)
    
    def test_product_pages_meta_tags(self):
        resp = self.client.get(self.product1_page.get_url())
        
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.product1_page, meta_tags, request=resp.wsgi_request)
        
        resp = self.client.get(self.product2_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.product2_page, meta_tags, request=resp.wsgi_request)
    
    def test_product_item_page_render(self):
        self.assertPageIsRenderable(self.product1_page_product_item_page)
    
    def test_product_item_page_meta_tags(self):
        resp = self.client.get(self.product1_page_product_item_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.product1_page_product_item_page, meta_tags, request=resp.wsgi_request)

    def test_product_listing_image_uses_introduction_image_first(self):
        product_page = self.product1_page.__class__.objects.get(
            pk=self.product1_page.pk
        )
        self.assertEqual(
            product_page.listing_image,
            product_page.introduction_image,
        )

    def test_product_listing_image_falls_back_to_latest_product_item(self):
        product_page = self.product1_page.__class__.objects.get(
            pk=self.product1_page.pk
        )
        product_page.introduction_image = None
        product_page.save(update_fields=["introduction_image"])

        self.assertEqual(
            product_page.listing_image,
            self.product1_page_product_item_page.products_listing_image,
        )

    def test_product_listing_image_uses_configured_default_when_empty(self):
        default_thumbnail = wagtail_factories.ImageFactory()
        product_page = self.product2_page.__class__.objects.get(
            pk=self.product2_page.pk
        )
        product_page.introduction_image = None
        product_page.default_listing_thumbnail = default_thumbnail
        product_page.save(
            update_fields=["introduction_image", "default_listing_thumbnail"]
        )

        self.assertEqual(product_page.listing_image, default_thumbnail)
