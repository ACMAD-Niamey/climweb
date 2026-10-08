from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.services.forms import TrainingProposalForm
from climweb.pages.services.models import (
    OnTheJobTrainingPage,
    MeteorologicalService,
    ServiceIndexPage,
    ServicePage,
    TrainingProposal,
    TrainingTopic,
)


class TestSeedOnTheJobTraining(WagtailPageTestCase):
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

    def test_command_creates_complete_editable_page(self):
        call_command("seed_on_the_job_training", stdout=StringIO())

        page = OnTheJobTrainingPage.objects.get(slug="on-the-job-training")
        self.assertTrue(page.live)
        self.assertEqual(page.get_parent().specific, self.home)
        self.assertEqual(len(page.training_modules), 13)
        self.assertEqual(len(page.application_steps), 3)
        self.assertEqual(len(page.testimonials), 2)
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Training offered")
        self.assertContains(response, "Visitor reports")
        self.assertContains(response, "Accommodation")
        self.assertContains(response, "Submit a training proposal")
        self.assertContains(response, "Proposed training title")
        self.assertContains(response, 'data-proposal-open')
        self.assertContains(response, 'href="#training-proposal-modal"')
        self.assertContains(response, 'id="training-proposal-modal"')
        self.assertNotContains(
            response,
            'href="mailto:secretariat@acmad.org">Contact the programme</a>',
        )

    def test_training_proposal_can_be_submitted_online(self):
        call_command("seed_on_the_job_training", stdout=StringIO())
        page = OnTheJobTrainingPage.objects.get(slug="on-the-job-training")
        organisation = MeteorologicalService.objects.create(
            country="Niger",
            name="National Meteorological Service",
            acronym="DMN",
            website_url="https://example.com",
        )
        topic = TrainingTopic.objects.create(name="Impact-based forecasting")

        response = self.client.post(
            page.url,
            {
                "form_id": "training-proposal",
                "full_name": "Amina Issoufou",
                "email": "amina@example.com",
                "phone": "+227 90 00 00 00",
                "country": "Niger",
                "organisation": organisation.pk,
                "job_title": "Meteorologist",
                "programme_type": "ojt",
                "proposal_title": topic.pk,
                "professional_background": "Operational forecaster supporting national warning services.",
                "objectives": "Improve severe weather and impact-based forecasting skills.",
                "expected_outcomes": "Apply impact-based forecasts across national warning operations.",
                "preferred_start_date": "2027-01-10",
                "preferred_end_date": "2027-03-10",
                "nomination_letter": SimpleUploadedFile(
                    "nomination.pdf", b"nomination"
                ),
                "cv": SimpleUploadedFile("cv.pdf", b"curriculum vitae"),
                "supporting_document": SimpleUploadedFile(
                    "motivation.pdf", b"motivation"
                ),
                "consent": "on",
                "website": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{page.url}?proposal=submitted")
        proposal = TrainingProposal.objects.get()
        self.assertEqual(proposal.page, page)
        self.assertEqual(proposal.full_name, "Amina Issoufou")
        self.assertEqual(proposal.organisation, organisation)
        self.assertEqual(proposal.proposal_title, topic)
        self.assertEqual(proposal.status, TrainingProposal.STATUS_NEW)

        confirmation = self.client.get(response.url)
        self.assertContains(confirmation, "Proposal received")
        self.assertContains(
            confirmation,
            'class="modal ojt-proposal-modal is-active"',
        )

    def test_every_public_proposal_field_is_required(self):
        form = TrainingProposalForm(data={})

        self.assertFalse(form.is_valid())
        required_fields = set(form.fields) - {"website"}
        self.assertTrue(required_fields.issubset(form.errors))

    def test_command_preserves_existing_page(self):
        call_command("seed_on_the_job_training", stdout=StringIO())
        page = OnTheJobTrainingPage.objects.get(slug="on-the-job-training")
        page.location = "Editor supplied location"
        page.save_revision().publish()

        call_command("seed_on_the_job_training", stdout=StringIO())
        page.refresh_from_db()

        self.assertEqual(page.location, "Editor supplied location")

    def test_admin_edit_page_renders_successfully(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="password",
        )
        call_command("seed_on_the_job_training", stdout=StringIO())
        page = OnTheJobTrainingPage.objects.get(slug="on-the-job-training")
        self.client.force_login(user)
        response = self.client.get(f"/cms-admin/pages/{page.id}/edit/")
        self.assertEqual(response.status_code, 200)
