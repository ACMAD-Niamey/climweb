from django.core.files.uploadedfile import SimpleUploadedFile
import wagtail_factories
from wagtail.rich_text import RichText
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.news.models import NEWS_ALLOWED_RICHTEXT_FEATURES
from .factories import NewsIndexPageFactory, NewsPageFactory


class TestNewsPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.index_page = NewsIndexPageFactory(parent=home_page)
        cls.news1 = NewsPageFactory(parent=cls.index_page)
        cls.news2 = NewsPageFactory(parent=cls.index_page, rich_text_field_with_image=True)
    
    def test_index_page_render(self):
        self.assertPageIsRenderable(self.index_page)
    
    def test_index_page_meta_tags(self):
        resp = self.client.get(self.index_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.index_page, meta_tags, request=resp.wsgi_request)
    
    def test_news_page_render(self):
        self.assertPageIsRenderable(self.news1)
        self.assertPageIsRenderable(self.news2)

    def test_news_gallery_renders_images_and_videos(self):
        image = wagtail_factories.ImageChooserBlockFactory()
        video = wagtail_factories.DocumentFactory(
            title="News recap",
            file=SimpleUploadedFile(
                "news-recap.mp4",
                b"test video content",
                content_type="video/mp4",
            ),
        )
        self.news1.media_gallery = [
            (
                "gallery",
                {
                    "title": "Event highlights",
                    "grid_style": "grid",
                    "columns": "3",
                    "images": [{"image": image, "caption": "Opening session"}],
                    "videos": [
                        (
                            "video",
                            {
                                "video": video,
                                "caption": "Uploaded event recap",
                                "poster": None,
                            },
                        ),
                        (
                            "hosted_video",
                            {
                                "url": "https://video.example.org/event-recap",
                                "title": "Watch the hosted recap",
                                "thumbnail": None,
                            },
                        ),
                    ],
                },
            ),
        ]
        self.news1.save_revision().publish()

        response = self.client.get(self.news1.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Event highlights")
        self.assertContains(response, "Opening session")
        self.assertContains(response, "Uploaded event recap")
        self.assertContains(response, video.url)
        self.assertContains(response, "Watch the hosted recap")
        self.assertContains(response, "https://video.example.org/event-recap")

    def test_existing_image_only_gallery_still_renders(self):
        image = wagtail_factories.ImageChooserBlockFactory()
        self.news1.media_gallery = [
            (
                "gallery",
                {
                    "title": "Photo archive",
                    "grid_style": "masonry",
                    "columns": "3",
                    "images": [{"image": image, "caption": "Archive photo"}],
                },
            ),
        ]
        self.news1.save_revision().publish()

        response = self.client.get(self.news1.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Photo archive")
        self.assertContains(response, "Archive photo")

    def test_news_body_supports_uploaded_and_hosted_videos(self):
        video = wagtail_factories.DocumentFactory(
            title="Body recap",
            file=SimpleUploadedFile(
                "body-recap.mp4",
                b"test video content",
                content_type="video/mp4",
            ),
        )
        self.news1.body_videos = [
            (
                "video",
                {
                    "video": video,
                    "caption": "Video within the article body",
                    "poster": None,
                },
            ),
            (
                "hosted_video",
                {
                    "url": "https://video.example.org/body-recap",
                    "title": "Watch the full interview",
                    "thumbnail": None,
                },
            ),
        ]
        self.news1.save_revision().publish()

        response = self.client.get(self.news1.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="nd-body-videos"')
        self.assertContains(response, "Video within the article body")
        self.assertContains(response, video.url)
        self.assertContains(response, "Watch the full interview")
        self.assertContains(response, "https://video.example.org/body-recap")
        self.assertIn("embed", NEWS_ALLOWED_RICHTEXT_FEATURES)

    def test_news_body_supports_quotes(self):
        self.news1.body = RichText(
            "<p>Article introduction.</p>"
            "<blockquote>Climate information must reach every community.</blockquote>"
        )
        self.news1.save_revision().publish()

        response = self.client.get(self.news1.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "<blockquote>Climate information must reach every community.</blockquote>",
            html=True,
        )
        self.assertIn("blockquote", NEWS_ALLOWED_RICHTEXT_FEATURES)
    
    def test_news_page_meta_tags(self):
        resp = self.client.get(self.news1.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.news1, meta_tags, check_image=False, request=resp.wsgi_request)
        
        resp = self.client.get(self.news2.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.news2, meta_tags, check_image=False, request=resp.wsgi_request)
