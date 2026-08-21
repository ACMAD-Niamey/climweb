from datetime import timedelta

from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import (
    EventIndexPageFactory,
    EventPageFactory,
    EventRegistrationPageFactory
)


class TestEventPages(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.page = EventIndexPageFactory(parent=home_page)
        
        cls.event1 = EventPageFactory(parent=cls.page)
        cls.event2 = EventPageFactory(parent=cls.page)
        
        cls.event1_reg = EventRegistrationPageFactory(parent=cls.event1)
    
    def test_index_page_rendering(self):
        self.assertPageIsRenderable(self.page)
    
    def test_index_page_meta_tags(self):
        resp = self.client.get(self.page.get_url())
        
        meta_tags = get_html_meta_tags(resp.content)
        
        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)
    
    def test_event_page_rendering(self):
        self.assertPageIsRenderable(self.event1)
        self.assertPageIsRenderable(self.event2)
    
    def test_event_page_meta_tags(self):
        resp = self.client.get(self.event1.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        test_page_meta_tags(self, self.event1, meta_tags, request=resp.wsgi_request)
    
    def test_event_registration_page_rendering(self):
        self.assertPageIsRenderable(self.event1_reg)
    
    def test_event_registration_page_meta_tags(self):
        resp = self.client.get(self.event1_reg.get_url())
        meta_tags = get_html_meta_tags(resp.content)
        test_page_meta_tags(self, self.event1_reg, meta_tags, request=resp.wsgi_request)


class TestEventRegistrationClosingDate(WagtailPageTestCase):
    """
    submissions_closing_date (FormPageClosingDateMixin) used to only drive
    the pre-deadline reminder email - it never actually stopped
    registrations after the date passed. is_closed
    (FormPageReviewSettingsMixin) + the serve() guard below fix that.
    """

    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        index_page = EventIndexPageFactory(parent=home_page)
        cls.event = EventPageFactory(parent=index_page)
        cls.registration_page = EventRegistrationPageFactory(parent=cls.event)

        cls.registration_page.registration_form_fields.create(
            label="Email address", field_type="email", required=True, sort_order=0,
        )
        cls.registration_page.save()

    def test_is_closed_false_when_no_closing_date_set(self):
        self.registration_page.submissions_closing_date = None
        self.assertFalse(self.registration_page.is_closed)

    def test_is_closed_false_on_closing_date_itself(self):
        self.registration_page.submissions_closing_date = timezone.now().date()
        self.assertFalse(self.registration_page.is_closed)

    def test_is_closed_true_after_closing_date(self):
        self.registration_page.submissions_closing_date = timezone.now().date() - timedelta(days=1)
        self.assertTrue(self.registration_page.is_closed)

    def test_get_rejects_form_after_closing_date(self):
        self.registration_page.submissions_closing_date = timezone.now().date() - timedelta(days=1)
        self.registration_page.save()

        response = self.client.get(self.registration_page.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"])

    def test_post_after_closing_date_does_not_create_a_submission(self):
        self.registration_page.submissions_closing_date = timezone.now().date() - timedelta(days=1)
        self.registration_page.save()

        submission_class = self.registration_page.get_submission_class()
        starting_count = submission_class.objects.filter(page=self.registration_page).count()

        self.client.post(self.registration_page.url, data={"email_address": "late@example.com"})

        self.assertEqual(
            submission_class.objects.filter(page=self.registration_page).count(),
            starting_count,
        )

    def test_registration_page_property_returns_specific_instance(self):
        # EventPage.registration_page must return the specific
        # EventRegistrationPage, not the base Page get_first_child()
        # returns - otherwise is_closed silently resolves to falsy in
        # templates instead of being evaluated at all.
        self.assertIsInstance(self.event.registration_page, type(self.registration_page))
