from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from .factories import StaffPageFactory
from ..models import Department, StaffMember


class TestStaffPage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        organisation_page = OrganisationIndexPageFactory(parent=home_page)
        cls.page = StaffPageFactory(parent=organisation_page)
        department = Department.objects.create(name="Climate Services")
        cls.member = StaffMember.objects.create(
            page=cls.page,
            name="Dr. Team Member",
            role="Climate Scientist",
            department=department,
            photo=cls.page.banner_image,
            bio="<p>Works on climate information and early warning.</p>",
        )
        cls.member_without_photo = StaffMember.objects.create(
            page=cls.page,
            name="New Team Member",
            role="Researcher",
            department=department,
        )
    
    def test_about_page_render(self):
        self.assertPageIsRenderable(self.page)
    
    def test_about_page_meta_tags(self):
        resp = self.client.get(self.page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)

    def test_trainer_style_cards_and_accessible_modals(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, 'class="staff-card"', count=2)
        self.assertContains(response, 'role="dialog"', count=2)
        self.assertContains(response, f'data-staff-modal="staff-modal-{self.member.pk}"')
        self.assertContains(response, f'aria-labelledby="staff-modal-name-{self.member.pk}"')
        self.assertContains(response, 'aria-hidden="true" tabindex="-1"', count=2)
        self.assertContains(response, "staff/css/staff_page.css")
        self.assertContains(response, "staff/js/staff_page.js")

    def test_biography_only_appears_in_modal(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, "Works on climate information and early warning.", count=1)
        self.assertContains(response, "View bio", count=1)
        self.assertContains(response, "View profile", count=1)

    def test_photo_fallback_and_descriptive_alt_text(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, 'alt="Dr. Team Member"', count=2)
        self.assertContains(response, "images/person.svg", count=2)
