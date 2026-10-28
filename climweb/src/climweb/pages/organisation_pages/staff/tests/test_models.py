from wagtail.test.utils import WagtailPageTestCase
from django.contrib.auth import get_user_model

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from climweb.pages.organisation_pages.board.tests.factories import DirectorGeneralPageFactory
from .factories import StaffPageFactory
from ..models import (
    Department,
    StaffMember,
    StaffPageDepartmentSelection,
    StaffPageSelection,
    StaffProfileAccess,
)


class TestStaffPage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        organisation_page = OrganisationIndexPageFactory(parent=home_page)
        cls.page = StaffPageFactory(parent=organisation_page)
        cls.director_general_page = DirectorGeneralPageFactory(parent=cls.page)
        department = Department.objects.create(name="Climate Services")
        cls.member = StaffMember.objects.create(
            page=cls.page,
            name="Dr. Team Member",
            role="Director General",
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
        StaffPageSelection.objects.create(page=cls.page, member=cls.member, sort_order=0)
        StaffPageSelection.objects.create(page=cls.page, member=cls.member_without_photo, sort_order=1)
    
    def test_about_page_render(self):
        self.assertPageIsRenderable(self.page)
    
    def test_about_page_meta_tags(self):
        resp = self.client.get(self.page.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)

    def test_trainer_style_cards_and_accessible_modals(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, 'class="staff-card"', count=2)
        self.assertContains(response, 'class="modal staff-modal" role="dialog"', count=2)
        self.assertContains(response, f'data-staff-modal="staff-modal-{self.member.pk}"')
        self.assertContains(response, f'aria-labelledby="staff-modal-name-{self.member.pk}"')
        self.assertContains(response, 'aria-hidden="true" tabindex="-1"', count=2)
        self.assertContains(response, 'data-staff-bio-toggle', count=1)
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, "Read more", count=2)
        self.assertContains(response, "staff/css/staff_page.css")
        self.assertContains(response, "staff/js/staff_page.js")

    def test_biography_only_appears_in_modal(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, "Works on climate information and early warning.", count=1)
        self.assertContains(response, "View bio", count=1)
        self.assertContains(response, "View profile", count=1)

    def test_staff_cards_have_shareable_modal_links(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(
            response,
            f'href="#staff-modal-{self.member.pk}" class="staff-card-trigger"',
        )

    def test_departments_follow_page_specific_drag_order(self):
        leadership = Department.objects.create(name="Leadership", order=99)
        leader = StaffMember.objects.create(
            page=self.page,
            name="Team Lead",
            role="Director",
            department=leadership,
        )
        StaffPageSelection.objects.create(page=self.page, member=leader, sort_order=2)
        StaffPageDepartmentSelection.objects.create(
            page=self.page,
            department=leadership,
            sort_order=0,
        )
        StaffPageDepartmentSelection.objects.create(
            page=self.page,
            department=self.member.department,
            sort_order=1,
        )

        html = self.client.get(self.page.get_url()).content.decode()
        self.assertLess(html.index("Leadership"), html.index("Climate Services"))

    def test_photo_fallback_and_descriptive_alt_text(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, 'alt="Dr. Team Member"', count=2)
        self.assertContains(response, "images/person.svg", count=2)

    def test_contact_icons_render_on_card_and_modal_outside_profile_trigger(self):
        self.member.website = "https://example.test/profile"
        self.member.linkedin = "https://www.linkedin.com/in/test"
        self.member.github = "https://github.com/test"
        self.member.publications = "https://example.test/publications"
        account = get_user_model().objects.create_user(username="contact-test", email="contact@example.test")
        StaffProfileAccess.objects.create(member=self.member, user=account)
        self.member.save()
        response = self.client.get(self.page.get_url())
        for url in [self.member.website, self.member.linkedin, self.member.github, self.member.publications, "mailto:contact@example.test"]:
            self.assertContains(response, f'href="{url}"', count=2)
        for label in ["Website", "LinkedIn", "GitHub", "Publications", "Email"]:
            self.assertContains(response, f'aria-label="{label} — {self.member.name}"', count=2)
        # Contact links are siblings of the profile trigger, never nested links.
        html = response.content.decode()
        for trigger in html.split('class="staff-card-trigger"')[1:]:
            self.assertNotIn("<a ", trigger.split("</a>")[0])
        for url in [self.member.website, self.member.linkedin, self.member.github, self.member.publications]:
            self.assertContains(response, f'href="{url}" target="_blank" rel="noopener noreferrer"', count=2)

    def test_blank_contact_fields_hide_icons(self):
        response = self.client.get(self.page.get_url())
        self.assertNotContains(response, 'class="staff-profile-links"')

    def test_director_general_modal_links_to_dedicated_page(self):
        response = self.client.get(self.page.get_url())
        self.assertContains(response, "View Director General's page")
        self.assertContains(response, f'href="{self.director_general_page.url}"')

    def test_mailto_encodes_query_characters_in_email_local_part(self):
        account = get_user_model().objects.create_user(username="email-escaping", email="contact?subject=test@example.test")
        StaffProfileAccess.objects.create(member=self.member, user=account)
        response = self.client.get(self.page.get_url())
        self.assertContains(response, 'href="mailto:contact%3Fsubject%3Dtest@example.test"', count=2)
