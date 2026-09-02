from io import StringIO

from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.services.models import (
    OnTheJobTrainingPage,
    ServiceIndexPage,
    ServicePage,
)


class TestSeedOnTheJobTraining(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        index = ServiceIndexPage(title="Services", slug="services")
        home.add_child(instance=index)
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

    def test_command_creates_complete_editable_page(self):
        call_command("seed_on_the_job_training", stdout=StringIO())

        page = OnTheJobTrainingPage.objects.get(slug="on-the-job-training")
        self.assertTrue(page.live)
        self.assertEqual(len(page.training_modules), 13)
        self.assertEqual(len(page.application_steps), 3)
        self.assertEqual(len(page.testimonials), 2)
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Training offered")
        self.assertContains(response, "Visitor reports")
        self.assertContains(response, "Accommodation")

    def test_command_preserves_existing_page(self):
        call_command("seed_on_the_job_training", stdout=StringIO())
        page = OnTheJobTrainingPage.objects.get(slug="on-the-job-training")
        page.location = "Editor supplied location"
        page.save_revision().publish()

        call_command("seed_on_the_job_training", stdout=StringIO())
        page.refresh_from_db()

        self.assertEqual(page.location, "Editor supplied location")
