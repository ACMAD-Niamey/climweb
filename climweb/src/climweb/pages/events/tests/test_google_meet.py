from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone
from googleapiclient.errors import HttpError
from wagtail.test.utils import WagtailPageTestCase
from wagtailzoom.models import AbstractZoomIntegrationForm

from climweb.pages.home.tests.factories import get_or_create_homepage

from ..google_meet import (
    build_calendar_event_body,
    calendar_payload_hash,
    deterministic_calendar_event_id,
    sync_google_meet_event,
)
from ..models import (
    EventMeeting,
    EventRegistrationDelivery,
    GoogleMeetSettings,
)
from ..tasks import (
    _retry_singleton_task,
    _send_registration_email,
    deliver_google_meet_registration,
)
from ..wagtail_hooks import enqueue_google_meet_sync
from .factories import (
    EventIndexPageFactory,
    EventPageFactory,
    EventRegistrationPageFactory,
)


class GoogleMeetTestCase(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        index_page = EventIndexPageFactory(parent=home_page)
        cls.event = EventPageFactory(parent=index_page)
        cls.event.attendance_mode = "online"
        cls.event.meeting_platform = "google_meet"
        cls.event.date_to = cls.event.date_from + timedelta(hours=2)
        cls.event.save()

        cls.registration_page = EventRegistrationPageFactory(parent=cls.event)
        cls.registration_page.email_field = "email_address"
        cls.registration_page.save()

        google_settings = GoogleMeetSettings.for_site(cls.event.get_site())
        google_settings.enabled = True
        google_settings.organizer_email = "events@example.org"
        google_settings.save()

    def test_online_event_requires_end_time(self):
        self.event.date_to = None
        with self.assertRaises(ValidationError) as error:
            self.event.clean()
        self.assertIn("date_to", error.exception.message_dict)

    def test_calendar_body_requests_unique_google_meet(self):
        meeting = EventMeeting.objects.create(
            event=self.event,
            calendar_event_id=deterministic_calendar_event_id(self.event),
        )

        body = build_calendar_event_body(
            self.event,
            meeting,
            include_conference=True,
        )

        self.assertEqual(
            body["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"],
            "hangoutsMeet",
        )
        self.assertEqual(body["start"]["timeZone"], "Africa/Nairobi")
        self.assertEqual(
            body["end"]["dateTime"],
            timezone.localtime(self.event.date_to, self.event.timezone).isoformat(),
        )

    @patch("climweb.pages.events.google_meet.get_calendar_service")
    def test_sync_creates_meeting_and_is_idempotent(self, get_service):
        not_found = HttpError(
            resp=SimpleNamespace(status=404, reason="Not Found"),
            content=b'{"error": {"message": "Not Found"}}',
        )
        events_api = Mock()
        events_api.get.return_value.execute.side_effect = not_found
        events_api.insert.return_value.execute.return_value = {
            "hangoutLink": "https://meet.google.com/abc-defg-hij",
        }
        get_service.return_value.events.return_value = events_api

        meeting = sync_google_meet_event(self.event)

        self.assertEqual(meeting.sync_status, EventMeeting.SyncStatus.READY)
        self.assertEqual(meeting.meet_url, "https://meet.google.com/abc-defg-hij")
        insert_kwargs = events_api.insert.call_args.kwargs
        self.assertEqual(insert_kwargs["conferenceDataVersion"], 1)
        self.assertEqual(insert_kwargs["sendUpdates"], "none")

        get_service.reset_mock()
        same_meeting = sync_google_meet_event(self.event)
        self.assertEqual(same_meeting.pk, meeting.pk)
        get_service.assert_not_called()

    @patch("climweb.pages.events.tasks._send_registration_email")
    @patch("climweb.pages.events.tasks.sync_google_meet_event")
    def test_delivery_emails_saved_registrant_once(self, sync_event, send_email):
        meeting = EventMeeting.objects.create(
            event=self.event,
            calendar_event_id=deterministic_calendar_event_id(self.event),
            meet_url="https://meet.google.com/abc-defg-hij",
            sync_status=EventMeeting.SyncStatus.READY,
        )
        sync_event.return_value = meeting
        submission = self.registration_page.get_submission_class().objects.create(
            page=self.registration_page,
            form_data={"email_address": "participant@example.com"},
        )

        deliver_google_meet_registration.run(self.registration_page.pk, submission.pk)
        deliver_google_meet_registration.run(self.registration_page.pk, submission.pk)

        delivery = EventRegistrationDelivery.objects.get(
            registration_page=self.registration_page,
            submission_id=submission.pk,
        )
        self.assertEqual(delivery.status, EventRegistrationDelivery.Status.SENT)
        self.assertEqual(delivery.email, "participant@example.com")
        self.assertEqual(delivery.attempts, 1)
        sync_event.assert_called_once_with(
            self.registration_page.event,
            force_remote_check=True,
        )
        send_email.assert_called_once_with(
            self.registration_page,
            "participant@example.com",
            meeting.meet_url,
        )

    def test_payload_hash_changes_when_schedule_changes(self):
        meeting = EventMeeting.objects.create(
            event=self.event,
            calendar_event_id=deterministic_calendar_event_id(self.event),
        )
        first = calendar_payload_hash(build_calendar_event_body(self.event, meeting))
        self.event.date_to += timedelta(hours=1)
        second = calendar_payload_hash(build_calendar_event_body(self.event, meeting))
        self.assertNotEqual(first, second)

    @patch("climweb.pages.events.tasks.deliver_google_meet_registration.delay")
    @patch.object(AbstractZoomIntegrationForm, "process_form_submission")
    def test_saved_registration_queues_google_delivery(self, process_submission, delay):
        process_submission.return_value = SimpleNamespace(pk=123)
        form = SimpleNamespace(
            fields={},
            cleaned_data={},
            is_valid=lambda: True,
        )
        self.registration_page.request = None

        with self.captureOnCommitCallbacks(execute=True):
            submission = self.registration_page.process_form_submission(form)

        self.assertEqual(submission.pk, 123)
        delay.assert_called_once_with(self.registration_page.pk, 123)

    def test_singleton_lock_is_released_before_retry_is_queued(self):
        task = Mock()
        task.request.args = (self.event.pk,)
        task.request.kwargs = {}
        task.request.retries = 2
        task.retry.side_effect = RuntimeError("retry queued")

        with self.assertRaisesMessage(RuntimeError, "retry queued"):
            _retry_singleton_task(task, ValueError("temporary error"))

        task.release_lock.assert_called_once_with(
            task_args=(self.event.pk,),
            task_kwargs={},
        )
        self.assertEqual(task.retry.call_args.kwargs["countdown"], 60)

    def test_participant_email_contains_private_meet_link(self):
        meet_url = "https://meet.google.com/abc-defg-hij"

        _send_registration_email(
            self.registration_page,
            "participant@example.com",
            meet_url,
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["participant@example.com"])
        self.assertIn(meet_url, mail.outbox[0].body)
        self.assertIn(self.event.title, mail.outbox[0].subject)

    def test_meet_link_is_not_exposed_on_public_event_page(self):
        meet_url = "https://meet.google.com/abc-defg-hij"
        EventMeeting.objects.create(
            event=self.event,
            calendar_event_id=deterministic_calendar_event_id(self.event),
            meet_url=meet_url,
            sync_status=EventMeeting.SyncStatus.READY,
        )

        response = self.client.get(self.event.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, meet_url)

    @patch("climweb.pages.events.tasks.sync_google_meet_event_task.delay")
    def test_publishing_google_event_queues_calendar_sync(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            enqueue_google_meet_sync(None, self.event)

        delay.assert_called_once_with(self.event.pk)

    @patch("climweb.pages.events.tasks.sync_google_meet_event_task.delay")
    def test_publishing_in_person_event_does_not_queue_sync(self, delay):
        self.event.attendance_mode = "in_person"

        with self.captureOnCommitCallbacks(execute=True):
            enqueue_google_meet_sync(None, self.event)

        delay.assert_not_called()
