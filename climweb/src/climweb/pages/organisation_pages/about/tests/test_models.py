import wagtail_factories
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from .factories import AboutPageFactory


class TestAboutPage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        organisation_page = OrganisationIndexPageFactory(parent=home_page)
        cls.page = AboutPageFactory(parent=organisation_page)
    
    def test_about_page_render(self):
        self.assertPageIsRenderable(self.page)
    
    def test_about_page_meta_tags(self):
        resp = self.client.get(self.page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)

    def test_timeline_milestone_title_links_to_supporting_document(self):
        document = wagtail_factories.DocumentFactory(title="ACMAD founding document")
        self.page.timeline = [
            (
                "nmhs_timeline",
                {
                    "year": "1987",
                    "milestones": [
                        {
                            "period": "December",
                            "description": "ACMAD was established",
                            "document": document,
                        }
                    ],
                },
            )
        ]
        self.page.save_revision().publish()

        response = self.client.get(self.page.get_url())

        self.assertContains(response, "ACMAD was established")
        self.assertContains(response, f'href="{document.url}"')
        self.assertContains(response, 'target="_blank" rel="noopener noreferrer"')
