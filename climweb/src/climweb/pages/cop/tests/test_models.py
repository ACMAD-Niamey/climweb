from datetime import date, datetime, timedelta

import wagtail_factories
from django.core.exceptions import ValidationError
from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.partners.tests.factories import PartnerFactory
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
                description="<p>ACMAD participation summary.</p>",
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
                description="<p>ACMAD at COP29.</p>",
            ),
        )
        cls.partner = PartnerFactory(name="African Climate Partner")
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
                theme="Climate resilience",
                lead_organizer=cls.partner,
                description="<p>Climate services side-event summary.</p>",
            ),
        )
        cls.side_event.partners.add(cls.partner)
        cls.side_event.save_revision().publish()

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

    def test_edition_uses_one_collapsible_description(self):
        response = self.client.get(self.current.url)
        self.assertContains(response, 'data-read-more')
        self.assertContains(response, 'data-read-more-toggle')
        self.assertContains(response, "ACMAD participation summary")

    def test_optional_logo_is_rendered_in_edition_title_row(self):
        logo = wagtail_factories.ImageFactory(title="COP31 logo")
        self.current.logo = logo
        self.current.save_revision().publish()

        response = self.client.get(self.current.url)
        self.assertContains(response, 'class="cop-edition-title-row"')
        self.assertContains(response, 'class="cop-edition-title-row__logo"')
        self.assertContains(response, "COP31 logo")

    def test_official_logo_replaces_visible_title_and_links_to_official_site(self):
        logo = wagtail_factories.ImageFactory(title="Official COP31 logo")
        self.current.logo = logo
        self.current.official_website_url = "https://cop31.example.org/"
        self.current.save_revision().publish()

        response = self.client.get(self.current.url)
        title_row = response.content.split(b'<div class="cop-edition-title-row">', 1)[1].split(
            b'<div class="cop-edition-overview__grid">', 1
        )[0]

        self.assertIn(b'class="is-sr-only">COP 31</h1>', title_row)
        self.assertIn(b'class="cop-edition-title-row__logo-link"', title_row)
        self.assertIn(b'href="https://cop31.example.org/"', title_row)
        self.assertNotContains(response, "Official COP website")

    def test_side_event_uses_compact_image_free_header_and_full_width_overview(self):
        self.side_event.featured_image = wagtail_factories.ImageFactory(title="Detail image")
        self.side_event.save_revision().publish()

        response = self.client.get(self.side_event.url)
        hero = response.content.split(b'<section class="cop-event-hero">', 1)[1].split(b"</section>", 1)[0]
        self.assertNotIn(b"<img", hero)
        self.assertContains(response, 'class="cop-event-hero__title"')
        self.assertContains(response, 'class="container cop-event-overview"')
        self.assertContains(response, 'class="cop-section-nav"')

    def test_side_events_default_to_list_with_grid_control_and_date_time(self):
        self.side_event.featured_image = wagtail_factories.ImageFactory(title="Hidden card image")
        self.side_event.save_revision().publish()

        with timezone.override("America/New_York"):
            response = self.client.get(self.current.url)
        self.assertContains(response, 'data-events-view="list"')
        self.assertContains(response, 'data-events-view="grid"')
        self.assertContains(response, 'class="cop-side-event-grid is-list"')
        self.assertContains(response, f'<a class="cop-side-event-card" href="{self.side_event.slug}/"')
        self.assertContains(response, 'class="cop-side-event-card__datetime"')
        self.assertContains(response, self.side_event.local_start_datetime.strftime("%-d %b"))
        self.assertContains(response, self.side_event.local_start_datetime.strftime("%H:%M"))
        self.assertNotContains(response, 'class="cop-side-event-card__image"')

    def test_edition_can_show_linkedin_follow_link(self):
        self.current.linkedin_url = "https://www.linkedin.com/company/acmad/"
        self.current.save_revision().publish()

        response = self.client.get(self.current.url)
        title_row = response.content.split(b'<div class="cop-edition-title-row">', 1)[1].split(
            b'<div class="cop-edition-overview__grid">', 1
        )[0]

        self.assertContains(response, "Follow us on LinkedIn")
        self.assertContains(response, self.current.linkedin_url)
        self.assertIn(b'cop-edition-title-row__follow', title_row)
        self.assertIn(self.current.linkedin_url.encode(), title_row)

    def test_acmad_co_organized_side_event_uses_green_card_treatment(self):
        self.side_event.acmad_is_co_organizer = True
        self.side_event.save_revision().publish()

        edition_response = self.client.get(self.current.url)
        side_event_response = self.client.get(self.side_event.url)

        self.assertContains(edition_response, "is-acmad-co-organized")
        self.assertContains(edition_response, "ACMAD co-organizer")
        self.assertContains(side_event_response, "Organizers")
        self.assertContains(side_event_response, "ACMAD co-organizer")
        self.assertContains(side_event_response, "cop-acmad-badge--on-primary")

    def test_edition_gallery_and_partners_match_side_event_components(self):
        gallery_image = wagtail_factories.ImageFactory(title="COP31 plenary")
        partner_logo = wagtail_factories.ImageFactory(title="Partner logo")
        self.partner.logo = partner_logo
        self.partner.save()
        self.current.gallery = [
            ("image", {"image": gallery_image, "caption": "COP31 plenary", "credit": "ACMAD"})
        ]
        self.current.partners.add(self.partner)
        self.current.save_revision().publish()

        response = self.client.get(self.current.url)

        self.assertContains(response, 'id="gallery"')
        self.assertContains(response, "data-gallery-carousel")
        self.assertContains(response, "data-gallery-scroll-previous")
        self.assertContains(response, "data-gallery-scroll-next")
        self.assertContains(response, 'id="partners"')
        self.assertContains(response, 'class="partner-card"')
        self.assertContains(response, 'class="image partner-logo-figure"')
        self.assertContains(response, "African Climate Partner")

    def test_schedule_flyer_is_rendered_in_carousel(self):
        document = wagtail_factories.DocumentFactory(title="COP31 schedule")
        flyer = wagtail_factories.ImageFactory(title="COP31 schedule flyer")
        self.current.schedule_documents = [
            ("document", {
                "title": "Week one schedule",
                "document": document,
                "preview_image": flyer,
                "description": "Programme flyer",
            })
        ]
        self.current.save_revision().publish()

        response = self.client.get(self.current.url)
        self.assertContains(response, 'data-schedule-carousel')
        self.assertContains(response, 'class="cop-schedule-slide__preview"')
        self.assertContains(response, "Week one schedule")

    def test_page_hierarchy_is_restricted(self):
        self.assertTrue(CopEditionPage.can_create_at(self.index))
        self.assertFalse(CopEditionPage.can_create_at(self.current))
        self.assertTrue(CopSideEventPage.can_create_at(self.current))
        self.assertFalse(CopSideEventPage.can_create_at(self.index))

    def test_concept_note_exists_only_on_side_event(self):
        self.assertNotIn("concept_note", {field.name for field in CopEditionPage._meta.fields})
        self.assertIn("concept_note", {field.name for field in CopSideEventPage._meta.fields})

    def test_consolidated_content_fields_replace_legacy_fields(self):
        edition_fields = {field.name for field in CopEditionPage._meta.fields}
        side_event_fields = {field.name for field in CopSideEventPage._meta.fields}
        self.assertIn("description", edition_fields)
        self.assertNotIn("acmad_participation", edition_fields)
        self.assertNotIn("about", edition_fields)
        self.assertNotIn("objectives", edition_fields)
        self.assertNotIn("expected_outcomes", edition_fields)
        self.assertIn("description", side_event_fields)
        self.assertIn("theme", side_event_fields)
        self.assertIn("lead_organizer", side_event_fields)
        self.assertNotIn("summary", side_event_fields)
        self.assertNotIn("objectives", side_event_fields)
        self.assertNotIn("participants", side_event_fields)

    def test_side_event_uses_partner_directory(self):
        response = self.client.get(self.side_event.url)
        self.assertContains(response, "Climate resilience")
        self.assertContains(response, "African Climate Partner")
        self.assertContains(response, 'id="partners"')
        self.assertContains(response, 'class="partner-card"')
        self.assertContains(response, 'class="image partner-logo-figure"')
        self.assertNotContains(response, "Collaboration")
        self.assertEqual(list(self.side_event.partners.all()), [self.partner])

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
            description="<p>Test</p>",
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
            description="<p>Test</p>",
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
        self.assertContains(response, 'data-gallery-carousel')
        self.assertContains(response, 'data-gallery-scroll-previous')
        self.assertContains(response, 'data-gallery-scroll-next')
        self.assertContains(response, "Panel discussion")
        self.assertNotContains(response, "<figcaption")
