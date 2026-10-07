from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import MediaIndexPageFactory


class MediaIndexPage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        
        cls.page = MediaIndexPageFactory(parent=home_page)
    
    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)
    
    def test_meta_tags(self):
        resp = self.client.get(self.page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)

    def test_latest_news_section_is_not_rendered(self):
        response = self.client.get(self.page.url)

        self.assertNotContains(response, "Latest News Updates")

    def test_introduction_video_replaces_image(self):
        self.page.introduction_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "intro-video-embed")

    def test_video_feature_item_is_rendered(self):
        self.page.feature_block_items = [
            (
                "feature_item",
                {
                    "figure_type": "video",
                    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "title": "Additional Media Center video",
                    "text": "A featured video item.",
                },
            )
        ]
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "media-feature-grid")
        self.assertContains(response, "fb-video-embed")
        self.assertContains(response, "Additional Media Center video")
