import json
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.blocks import ParticipantMapBlock
from climweb.base.models import CapacityBuildingParticipant, ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.services.models import (
    OnTheJobTrainingPage,
    ServiceIndexPage,
    ServicePage,
)


def _make(full_name, country, **kwargs):
    defaults = dict(
        gender="undisclosed",
        category="ojt",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 8, 1),
        is_active=True,
    )
    defaults.update(kwargs)
    return CapacityBuildingParticipant.objects.create(full_name=full_name, country=country, **defaults)


def _all_strings(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from _all_strings(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _all_strings(value)
    else:
        yield str(obj)


class AggregateByCountryTests(TestCase):
    def test_counts_gender_and_category_breakdown(self):
        _make("A", "KE", gender="female", category="ojt")
        _make("B", "KE", gender="male", category="secondment")
        _make("C", "KE", gender="female", category="ojt")
        _make("D", "NG", gender="male", category="ojt")

        result = CapacityBuildingParticipant.aggregate_by_country()

        self.assertEqual(set(result), {"KEN", "NGA"})
        self.assertEqual(result["KEN"]["total"], 3)
        self.assertEqual(result["KEN"]["iso_a2"], "KE")
        self.assertEqual(result["KEN"]["name"], "Kenya")
        self.assertEqual(result["KEN"]["by_gender"], {"female": 2, "male": 1})
        self.assertEqual(result["KEN"]["by_category"], {"ojt": 2, "secondment": 1})
        self.assertEqual(result["NGA"]["total"], 1)

    def test_inactive_records_excluded(self):
        _make("A", "KE")
        _make("B", "KE", is_active=False)
        result = CapacityBuildingParticipant.aggregate_by_country()
        self.assertEqual(result["KEN"]["total"], 1)

    def test_category_filter(self):
        _make("A", "KE", category="ojt")
        _make("B", "KE", category="secondment")
        result = CapacityBuildingParticipant.aggregate_by_country(categories=["secondment"])
        self.assertEqual(result["KEN"]["total"], 1)
        self.assertEqual(result["KEN"]["by_category"], {"secondment": 1})

    def test_date_window_overlap(self):
        _make("Past", "KE", start_date=date(2023, 1, 1), end_date=date(2023, 6, 1))
        _make("Spanning", "KE", start_date=date(2023, 12, 1), end_date=date(2024, 3, 1))
        _make("Ongoing", "KE", start_date=date(2024, 1, 1), end_date=None)

        result = CapacityBuildingParticipant.aggregate_by_country(
            date_from=date(2024, 1, 1), date_to=date(2024, 12, 31)
        )
        # "Past" ends before the window; the other two overlap it.
        self.assertEqual(result["KEN"]["total"], 2)

    def test_output_never_contains_participant_names(self):
        _make("Jane Verywell Smith", "KE")
        _make("John Distinctive Doe", "NG")
        result = CapacityBuildingParticipant.aggregate_by_country()
        blob = " ".join(_all_strings(result))
        self.assertNotIn("Verywell", blob)
        self.assertNotIn("Distinctive", blob)


class ParticipantMapBlockTests(TestCase):
    def test_get_context_is_aggregate_only(self):
        _make("Secret Name Person", "KE")
        block = ParticipantMapBlock()
        value = block.to_python({
            "heading": "Map",
            "introduction": "",
            "categories": [],
            "show_legend": True,
        })
        context = block.get_context(value)

        self.assertEqual(context["total_participants"], 1)
        self.assertIn("KEN", context["participants_by_country"])
        blob = " ".join(_all_strings(context["participants_by_country"]))
        self.assertNotIn("Secret", blob)
        self.assertIn("boundariesUrl", context["participant_map_config"])


class SeedDemoParticipantsTests(TestCase):
    def test_seed_command_is_idempotent(self):
        call_command("seed_capacity_building_participants", stdout=StringIO())
        first = CapacityBuildingParticipant.objects.count()
        self.assertEqual(first, 18)

        call_command("seed_capacity_building_participants", stdout=StringIO())
        self.assertEqual(CapacityBuildingParticipant.objects.count(), 18)

    def test_seed_reproduces_reference_map_totals(self):
        call_command("seed_capacity_building_participants", stdout=StringIO())
        result = CapacityBuildingParticipant.aggregate_by_country()
        self.assertEqual(result["COM"]["total"], 5)
        self.assertEqual(result["BEN"]["total"], 2)
        self.assertEqual(result["TGO"]["total"], 1)


class OnTheJobTrainingParticipantMapTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = get_or_create_homepage()
        index = ServiceIndexPage(title="Services", slug="services")
        cls.home.add_child(instance=index)
        category = ServiceCategory.objects.create(name="Capacity Development")
        parent = ServicePage(
            title="Capacity Development",
            slug="capacity-building",
            service=category,
            banner_title="Capacity Development",
            introduction_title="Capacity Development",
            introduction_text="<p>Training</p>",
        )
        index.add_child(instance=parent)
        parent.save_revision().publish()
        cls.parent = parent

    def _make_page(self, **kwargs):
        page = OnTheJobTrainingPage(
            title="OJT",
            slug="ojt",
            banner_title="OJT",
            introduction_title="OJT",
            introduction_text="<p>x</p>",
            objectives="<p>o</p>",
            eligibility="<p>e</p>",
            benefits="<p>b</p>",
            **kwargs,
        )
        self.parent.add_child(instance=page)
        page.save_revision().publish()
        return page

    def test_section_hidden_by_default(self):
        page = self._make_page()
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="participants"')

    def test_section_shown_when_enabled_and_hides_names(self):
        _make("Totally Unique Trainee", "KE")
        page = self._make_page(show_participant_map=True, participant_map_heading="Our reach")
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="participants"')
        self.assertContains(response, "Our reach")
        self.assertNotContains(response, "Totally Unique Trainee")


class ParticipantMapBlockRenderTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = get_or_create_homepage()

    def test_block_renders_on_flex_page_without_names(self):
        from climweb.pages.flex_page.models import FlexPage

        _make("Hidden Person Name", "KE")
        page = FlexPage(
            title="About us",
            slug="about-us",
            banner_title="About us",
            content=[("participant_map", {"heading": "Our reach", "show_legend": True})],
        )
        self.home.add_child(instance=page)
        page.save_revision().publish()

        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Our reach")
        self.assertContains(response, "participant-map__canvas")
        self.assertNotContains(response, "Hidden Person Name")


class ParticipantMapBoundariesViewTests(TestCase):
    def test_returns_bundled_africa_geojson_by_default(self):
        response = self.client.get("/api/participant-map/boundaries")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["type"], "FeatureCollection")
        isos = {f["properties"]["iso_a3"] for f in data["features"]}
        self.assertIn("KEN", isos)
        self.assertIn("COM", isos)

    def test_uploaded_geojson_override_is_normalised(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from wagtail.models import Site

        from climweb.base.models import ParticipantMapSettings

        custom = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ADM0_A3": "ken", "COUNTRY": "Kenya"},
                    "geometry": {"type": "Point", "coordinates": [37, 0]},
                }
            ],
        }
        site = Site.objects.get(is_default_site=True)
        settings_obj = ParticipantMapSettings.for_site(site)
        settings_obj.boundary_file = SimpleUploadedFile(
            "custom.geojson", json.dumps(custom).encode(), content_type="application/geo+json"
        )
        settings_obj.iso3_property = "ADM0_A3"
        settings_obj.name_property = "COUNTRY"
        settings_obj.save()

        response = self.client.get("/api/participant-map/boundaries")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["features"]), 1)
        self.assertEqual(data["features"][0]["properties"]["iso_a3"], "KEN")
        self.assertEqual(data["features"][0]["properties"]["name"], "Kenya")

    def test_clean_rejects_unparseable_upload(self):
        from django.core.exceptions import ValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile
        from wagtail.models import Site

        from climweb.base.models import ParticipantMapSettings

        site = Site.objects.get(is_default_site=True)
        settings_obj = ParticipantMapSettings.for_site(site)
        settings_obj.boundary_file = SimpleUploadedFile(
            "broken.geojson", b"not json at all", content_type="application/geo+json"
        )
        with self.assertRaises(ValidationError):
            settings_obj.clean()
