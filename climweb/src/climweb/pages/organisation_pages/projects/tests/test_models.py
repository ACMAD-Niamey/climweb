from django.test import RequestFactory
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from climweb.pages.organisation_pages.partners.tests.factories import PartnerFactory
from ..models import ProjectPage, ProjectSector
from .factories import ProjectsIndexPageFactory, ProjectPageFactory


class TestAboutPage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        organisation_page = OrganisationIndexPageFactory(parent=home_page)
        cls.index_page = ProjectsIndexPageFactory(parent=organisation_page)
        
        cls.project1 = ProjectPageFactory(parent=cls.index_page)
        cls.project2 = ProjectPageFactory(parent=cls.index_page)
    
    def test_index_page_render(self):
        self.assertPageIsRenderable(self.index_page)
    
    def test_index_page_meta_tags(self):
        resp = self.client.get(self.index_page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.index_page, meta_tags, request=resp.wsgi_request)
    
    def test_project_page_render(self):
        self.assertPageIsRenderable(self.project1)
        self.assertPageIsRenderable(self.project2)
    
    def test_project_page_meta_tags(self):
        resp = self.client.get(self.project1.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.project1, meta_tags, request=resp.wsgi_request)
        
        resp = self.client.get(self.project2.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.project2, meta_tags, request=resp.wsgi_request)

    def test_projects_can_be_filtered_by_donor(self):
        donor = PartnerFactory(name="Climate Fund")
        self.project1.partners.add(donor)
        self.project1.save_revision().publish()

        request = RequestFactory().get("/projects/", {"donor": donor.pk})
        projects = self.index_page.filter_projects(request)

        self.assertQuerySetEqual(projects, [self.project1], transform=lambda project: project)

    def test_projects_can_be_filtered_by_sector(self):
        sector = ProjectSector.objects.create(name="Agriculture")
        self.project2.sectors.add(sector)
        self.project2.save_revision().publish()

        request = RequestFactory().get("/projects/", {"sector": sector.pk})
        projects = self.index_page.filter_projects(request)

        self.assertQuerySetEqual(projects, [self.project2], transform=lambda project: project)

    def test_donor_and_sector_filters_are_displayed(self):
        donor = PartnerFactory(name="Development Partner")
        sector = ProjectSector.objects.create(name="Water")
        self.project1.partners.add(donor)
        self.project1.sectors.add(sector)
        self.project1.save_revision().publish()

        response = self.client.get(self.index_page.get_url())

        self.assertContains(response, "Filter by Donor")
        self.assertContains(response, donor.name)
        self.assertContains(response, "Filter by Sector")
        self.assertContains(response, sector.name)

    def test_project_sector_is_required_in_editor(self):
        self.assertFalse(ProjectPage._meta.get_field("sectors").blank)
