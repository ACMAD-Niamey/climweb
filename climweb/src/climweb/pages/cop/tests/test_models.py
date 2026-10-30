from datetime import date, datetime, timedelta

import wagtail_factories
from django.core.exceptions import ValidationError
from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.home.tests.factories import get_or_create_homepage
from ..models import CopEditionPage, CopIndexPage, CopSideEventPage


def publish_child(parent, page):
    parent.add_child(instance=page)
    page.save_revision().publish()
    return page


class TestCopPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        cls.index = publish_child(
            home,
            CopIndexPage(
                title="COP",
                slug="cop",
                introduction="<p>ACMAD participation at UN climate conferences.</p>",
            ),
        )
        cls.current = publish_child(
            cls.index,
            CopEditionPage(
                title="COP 31",
                slug="cop31",
                cop_number=31,
                is_current=True,
                start_date=date(2026, 11, 9),
                end_date=date(2026, 11, 20),
                host_city="Antalya",
                host_country="Türkiye",
                acmad_participation="<p>ACMAD participation summary.</p>",
                primary_color="#123456",
                secondary_color="#d6a83b",
                accent_color="#e6f3ee",
                text_on_primary_color="#ffffff",
            ),
        )
        cls.previous = publish_child(
            cls.index,
            CopEditionPage(
                title="COP 29",
                slug="cop29",
                cop_number=29,
                start_date=date(2024, 11, 11),
                end_date=date(2024, 11, 22),
                host_city="Baku",
                host_country="Azerbaijan",
                acmad_participation="<p>ACMAD at COP29.</p>",
            ),
        )
        start = timezone.make_aware(datetime(2026, 11, 10, 12, 0))
        cls.side_event = publish_child(
            cls.current,
            CopSideEventPage(
                title="Climate services for disaster risk reduction",
                slug="climate-services-for-disaster-risk-reduction",
                side_event_number=1,
                start_datetime=start,
                end_datetime=start + timedelta(hours=1, minutes=30),
                venue="African Pavilion",
                summary="<p>Climate services side-event summary.</p>",
            ),
        )

    def test_pages_render(self):
        self.assertPageIsRenderable(self.index)
        self.assertPageIsRenderable(self.current)
        self.assertPageIsRenderable(self.side_event)

    def test_landing_page_uses_marked_current_edition(self):
        self.assertEqual(self.index.current_edition, self.current)
        response = self.client.get(self.index.url)
        self.assertContains(response, "COP31")
        self.assertContains(response, "COP29")
        self.assertContains(response, "Previous COP editions")

    def test_edition_lists_child_side_events(self):
        self.assertEqual(list(self.current.side_events), [self.side_event])
        response = self.client.get(self.current.url)
        self.assertContains(response, self.side_event.title)
        self.assertContains(response, "African Pavilion")

    def test_edition_theme_is_rendered_as_css_variables(self):
        response = self.client.get(self.current.url)
        self.assertContains(response, "--cop-primary: #123456")
        self.assertContains(response, "--cop-on-primary: #ffffff")

    def test_edition_uses_legacy_opening_layout_without_section_navigation(self):
        response = self.client.get(self.current.url)
        self.assertContains(response, 'class="cop-edition-overview__grid"')
        self.assertContains(response, 'class="cop-edition-facts"')
        self.assertContains(response, "Start date")
        self.assertContains(response, "End date")
        self.assertContains(response, "Location")
        self.assertNotContains(response, 'class="cop-section-nav"')

    def test_edition_overview_uses_one_stacked_card_without_taglines(self):
        self.current.about = "<p>About this COP.</p>"
        self.current.objectives = "<p>Edition objectives.</p>"
        self.current.expected_outcomes = "<p>Expected results.</p>"
        self.current.save_revision().publish()

        response = self.client.get(self.current.url)
        self.assertContains(response, 'class="cop-overview-card"', count=1)
        self.assertContains(response, 'id="about"')
        self.assertContains(response, 'id="objectives"')
        self.assertContains(response, 'id="outcomes"')
        self.assertNotContains(response, "Our participation")
        self.assertNotContains(response, "Context")
        self.assertNotContains(response, "Priorities")
        self.assertNotContains(response, "Looking ahead")

    def test_page_hierarchy_is_restricted(self):
        self.assertTrue(CopEditionPage.can_create_at(self.index))
        self.assertFalse(CopEditionPage.can_create_at(self.current))
        self.assertTrue(CopSideEventPage.can_create_at(self.current))
        self.assertFalse(CopSideEventPage.can_create_at(self.index))

    def test_concept_note_exists_only_on_side_event(self):
        self.assertNotIn("concept_note", {field.name for field in CopEditionPage._meta.fields})
        self.assertIn("concept_note", {field.name for field in CopSideEventPage._meta.fields})

    def test_side_event_has_no_livestream_or_recording_fields(self):
        field_names = {field.name for field in CopSideEventPage._meta.fields}
        self.assertNotIn("livestream", field_names)
        self.assertNotIn("recording", field_names)
        self.assertNotIn("external_url", field_names)

    def test_edition_rejects_end_date_before_start_date(self):
        page = CopEditionPage(
            title="Invalid COP",
            slug="invalid-cop",
            cop_number=99,
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 9),
            host_city="Test",
            host_country="Test",
            acmad_participation="<p>Test</p>",
        )
        with self.assertRaises(ValidationError):
            page.full_clean()

    def test_side_event_rejects_end_time_before_start_time(self):
        start = timezone.make_aware(datetime(2026, 11, 10, 12, 0))
        page = CopSideEventPage(
            title="Invalid side event",
            slug="invalid-side-event",
            side_event_number=99,
            start_datetime=start,
            end_datetime=start - timedelta(minutes=30),
            venue="Test pavilion",
            summary="<p>Test</p>",
        )
        with self.assertRaises(ValidationError):
            page.full_clean()

    def test_gallery_renders_only_when_populated(self):
        response = self.client.get(self.side_event.url)
        self.assertNotContains(response, 'id="gallery"')

        image = wagtail_factories.ImageFactory(title="COP side event discussion")
        self.side_event.gallery = [
            ("image", {"image": image, "caption": "Panel discussion", "credit": "ACMAD"})
        ]
        self.side_event.save_revision().publish()

        response = self.client.get(self.side_event.url)
        self.assertContains(response, 'id="gallery"')
        self.assertContains(response, "Panel discussion")
        self.assertContains(response, "ACMAD")

