from datetime import timedelta

from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.seo_utils import get_html_meta_tags
from climweb.base.test_utils import test_page_meta_tags
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import DataRequestPageFactory


class TestDataRequestPage(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()

        cls.page = DataRequestPageFactory(parent=home_page)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)

    def test_meta_tags(self):
        resp = self.client.get(self.page.get_url())

        meta_tags = get_html_meta_tags(resp.content)

        test_page_meta_tags(self, self.page, meta_tags, request=resp.wsgi_request)


class TestDataRequestPageClosingDate(WagtailPageTestCase):
    """
    submissions_closing_date (FormPageClosingDateMixin) used to only drive
    the pre-deadline reminder email - it never actually stopped submissions
    after the date passed. is_closed (FormPageReviewSettingsMixin) + the
    serve() guard below fix that.
    """

    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.page = DataRequestPageFactory(parent=home_page)

        cls.email_field = cls.page.datarequest_form_fields.create(
            label="Email address", field_type="email", required=True, sort_order=0,
        )
        cls.page.save()

    def test_is_closed_false_when_no_closing_date_set(self):
        self.assertFalse(self.page.is_closed)

    def test_is_closed_true_after_closing_date(self):
        self.page.submissions_closing_date = timezone.now().date() - timedelta(days=1)
        self.assertTrue(self.page.is_closed)

    def test_get_rejects_form_after_closing_date(self):
        self.page.submissions_closing_date = timezone.now().date() - timedelta(days=1)
        self.page.save()

        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"])

    def test_post_after_closing_date_does_not_create_a_submission(self):
        self.page.submissions_closing_date = timezone.now().date() - timedelta(days=1)
        self.page.save()

        submission_class = self.page.get_submission_class()
        starting_count = submission_class.objects.filter(page=self.page).count()

        self.client.post(self.page.url, data={"email_address": "late@example.com"})

        self.assertEqual(
            submission_class.objects.filter(page=self.page).count(),
            starting_count,
        )


class TestDataRequestPageManualClose(WagtailPageTestCase):
    """
    Data Request has no natural deadline, so it also gets a manual on/off
    switch (form_open, FormPageManualCloseMixin) independent of the closing
    date - editors can stop accepting submissions immediately.
    """

    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.page = DataRequestPageFactory(parent=home_page)

        cls.email_field = cls.page.datarequest_form_fields.create(
            label="Email address", field_type="email", required=True, sort_order=0,
        )
        cls.page.save()

    def test_form_open_by_default(self):
        self.assertTrue(self.page.form_open)
        self.assertFalse(self.page.is_closed)

    def test_is_closed_when_form_open_is_off(self):
        self.page.form_open = False
        self.assertTrue(self.page.is_closed)

    def test_is_closed_when_form_open_is_off_even_with_future_closing_date(self):
        self.page.form_open = False
        self.page.submissions_closing_date = timezone.now().date() + timedelta(days=30)
        self.assertTrue(self.page.is_closed)

    def test_get_rejects_form_when_form_open_is_off(self):
        self.page.form_open = False
        self.page.save()

        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"])
