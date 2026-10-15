from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.organisation.models import OrganisationIndexPage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from climweb.pages.organisation_pages.staff.models import Department, StaffMember, StaffPage, StaffPageSelection
from climweb.pages.organisation_pages.staff.tests.factories import StaffPageFactory

from ..models import BoardMember, BoardPage, BoardPresidentPage, DirectorGeneralPage
from .factories import BoardPageFactory, BoardPresidentPageFactory, DirectorGeneralPageFactory


class TestBoardPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        organisation_page = OrganisationIndexPageFactory(parent=home_page)
        cls.board_page = BoardPageFactory(parent=organisation_page)
        cls.president_page = BoardPresidentPageFactory(parent=cls.board_page)
        cls.staff_page = StaffPageFactory(parent=organisation_page)
        department = Department.objects.create(name="Executive Office")
        cls.director_general = StaffMember.objects.create(
            page=cls.staff_page,
            name="Dr. Director General",
            role="Director General",
            department=department,
            bio="<p>A leader committed to climate services.</p>",
        )
        StaffPageSelection.objects.create(page=cls.staff_page, member=cls.director_general)
        cls.director_general_page = DirectorGeneralPageFactory(parent=cls.staff_page)
        cls.member = BoardMember.objects.create(
            page=cls.board_page,
            name="Dr. Governor",
            role="Governor",
            country="Niger",
            biography="<p>Supports regional climate cooperation.</p>",
        )

    def test_board_page_is_renderable(self):
        self.assertPageIsRenderable(self.board_page)

    def test_board_page_shows_president_link_and_member_modal(self):
        response = self.client.get(self.board_page.get_url())
        self.assertContains(response, "Dr. Board President")
        self.assertContains(response, self.president_page.get_url())
        self.assertContains(response, "Dr. Governor", count=2)
        self.assertContains(response, f'data-board-modal="board-modal-{self.member.pk}"')
        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, "Supports regional climate cooperation.", count=1)

    def test_president_page_is_renderable(self):
        self.assertPageIsRenderable(self.president_page)

    def test_president_page_contains_bio_and_vision(self):
        response = self.client.get(self.president_page.get_url())
        self.assertContains(response, "A leader committed to climate resilience.")
        self.assertContains(response, "Vision for ACMAD")
        self.assertContains(response, "A safer, climate-resilient Africa.")
        self.assertContains(response, self.board_page.get_url())

    def test_president_page_inherits_on_the_job_training_design_system(self):
        response = self.client.get(self.president_page.get_url())
        self.assertContains(response, "css/on_the_job_training.css")
        self.assertContains(response, "ojt-page board-president-page")
        self.assertNotContains(response, 'class="ojt-nav"')
        self.assertContains(response, 'class="ojt-intro president-profile"')
        self.assertContains(response, 'class="ojt-section ojt-muted president-vision-section"')
        html = response.content.decode()
        self.assertLess(
            html.index("president-profile-portrait"),
            html.index("president-profile-copy"),
        )
        self.assertLess(
            html.index("president-profile-copy"),
            html.index("president-biography"),
        )

    def test_director_general_page_is_renderable(self):
        self.assertPageIsRenderable(self.director_general_page)

    def test_director_general_page_contains_profile_and_inaugural_speech(self):
        response = self.client.get(self.director_general_page.get_url())
        self.assertContains(response, "Dr. Director General")
        self.assertNotContains(response, "A leader committed to climate services.")
        self.assertNotContains(response, "Vision for ACMAD")
        self.assertContains(response, "Inaugural Speech")
        self.assertContains(response, "Together, we will strengthen ACMAD.")
        self.assertContains(response, "Director General of ACMAD")
        self.assertContains(response, "ojt-page board-president-page director-general-page")
        self.assertContains(response, 'class="dg-profile-image-frame"')

    def test_page_type_relationships(self):
        self.assertAllowedParentPageTypes(BoardPage, {OrganisationIndexPage})
        self.assertAllowedSubpageTypes(BoardPage, {BoardPresidentPage})
        self.assertAllowedParentPageTypes(BoardPresidentPage, {BoardPage})
        self.assertAllowedSubpageTypes(BoardPresidentPage, set())
        self.assertAllowedParentPageTypes(DirectorGeneralPage, {StaffPage})
        self.assertAllowedSubpageTypes(DirectorGeneralPage, set())
