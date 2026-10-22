from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from loguru import logger
from wagtail.rich_text import expand_db_html

from celery_singleton import Singleton

from climweb.config.celery import app

from .google_meet import sync_google_meet_event
from .models import (
    EventMeeting,
    EventPage,
    EventRegistrationDelivery,
    EventRegistrationPage,
    GoogleMeetSettings,
)


def _retry_countdown(retries):
    return min(15 * (2 ** retries), 300)


def _retry_singleton_task(task, exc):
    """Release celery-singleton's lock before Celery enqueues the retry."""

    # celery-singleton only releases locks in on_success/on_failure. A Celery
    # Retry is neither, and retry() calls apply_async immediately, so leaving
    # the lock in place makes the replacement message look like a duplicate.
    task.release_lock(
        task_args=task.request.args,
        task_kwargs=task.request.kwargs,
    )
    raise task.retry(
        exc=exc,
        countdown=_retry_countdown(task.request.retries),
    )


def _record_meeting_error(event_id, exc, final=False):
    EventMeeting.objects.filter(event_id=event_id).update(
        sync_status=(
            EventMeeting.SyncStatus.FAILED
            if final
            else EventMeeting.SyncStatus.PENDING
        ),
        last_error=str(exc)[:4000],
    )


@app.task(bind=True, base=Singleton, max_retries=6, lock_expiry=900)
def sync_google_meet_event_task(self, event_id):
    """Create/update a Meet conference after an online event is published."""

    try:
        event = EventPage.objects.get(pk=event_id)
        if not event.uses_google_meet:
            return
        sync_google_meet_event(event)
    except Exception as exc:
        final = self.request.retries >= self.max_retries
        _record_meeting_error(event_id, exc, final=final)
        logger.error(f"[GOOGLE_MEET] Event sync failed for {event_id}: {exc}")
        if final:
            mail_admins(
                subject="Google Meet event synchronization failed",
                message=f"Event page ID: {event_id}\n\n{exc}",
                fail_silently=True,
            )
            raise
        _retry_singleton_task(self, exc)


def _submission_email(registration_page, form_data):
    candidates = (
        registration_page.email_field,
        "email",
        "email_address",
    )
    for field_name in candidates:
        if field_name and form_data.get(field_name):
            return str(form_data[field_name]).strip()
    return ""


def _expanded_confirmation_message(registration_page):
    raw_message = registration_page.email_confirmation_message
    if not raw_message:
        return "", ""
    source = raw_message.source if hasattr(raw_message, "source") else str(raw_message)
    html = expand_db_html(source) if source.strip().startswith("<") else ""
    return html, strip_tags(html) if html else source


def _send_registration_email(registration_page, email, meet_url):
    event = registration_page.event
    integration_settings = GoogleMeetSettings.for_site(event.get_site())
    subject_template = (
        integration_settings.participant_email_subject
        or "You're registered: {event_title}"
    )
    subject = subject_template.replace("{event_title}", event.title)
    custom_html, custom_text = _expanded_confirmation_message(registration_page)
    context = {
        "event": event,
        "meet_url": meet_url,
        "custom_html": custom_html,
        "custom_text": custom_text,
        "start_at": timezone.localtime(event.date_from, event.timezone),
        "end_at": timezone.localtime(event.date_to, event.timezone),
    }
    text_body = render_to_string(
        "events/google_meet_registration_email.txt",
        context,
    )
    html_body = render_to_string(
        "events/google_meet_registration_email.html",
        context,
    )
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


@app.task(bind=True, base=Singleton, max_retries=6, lock_expiry=900)
def deliver_google_meet_registration(self, registration_page_id, submission_id):
    """Email the private Meet URL to one successfully saved registration."""

    registration_page = EventRegistrationPage.objects.get(pk=registration_page_id)
    submission = registration_page.get_submission_class().objects.get(
        pk=submission_id,
        page=registration_page,
    )
    form_data = submission.get_data()
    email = _submission_email(registration_page, form_data)

    delivery, _ = EventRegistrationDelivery.objects.get_or_create(
        registration_page=registration_page,
        submission_id=submission_id,
        defaults={"email": email},
    )
    if delivery.status == EventRegistrationDelivery.Status.SENT:
        return

    delivery.email = email
    delivery.status = EventRegistrationDelivery.Status.PROCESSING
    delivery.attempts += 1
    delivery.last_error = ""
    delivery.save(update_fields=(
        "email",
        "status",
        "attempts",
        "last_error",
        "updated_at",
    ))

    try:
        if not email:
            raise ValueError(
                "The saved registration does not contain the configured email field."
            )
        # Verify the remote event for every new delivery so a Calendar event
        # deleted outside ClimWeb cannot leave us emailing a stale Meet URL.
        meeting = sync_google_meet_event(
            registration_page.event,
            force_remote_check=True,
        )
        _send_registration_email(registration_page, email, meeting.meet_url)
    except Exception as exc:
        final = self.request.retries >= self.max_retries
        delivery.status = (
            EventRegistrationDelivery.Status.FAILED
            if final
            else EventRegistrationDelivery.Status.PENDING
        )
        delivery.last_error = str(exc)[:4000]
        delivery.save(update_fields=("status", "last_error", "updated_at"))
        logger.error(
            "[GOOGLE_MEET] Registration delivery failed for "
            f"submission {submission_id}: {exc}"
        )
        if final:
            mail_admins(
                subject="Google Meet registration email failed",
                message=(
                    f"Registration page ID: {registration_page_id}\n"
                    f"Submission ID: {submission_id}\n"
                    f"Participant: {email or '(email field missing)'}\n\n{exc}"
                ),
                fail_silently=True,
            )
            raise
        _retry_singleton_task(self, exc)

    delivery.status = EventRegistrationDelivery.Status.SENT
    delivery.sent_at = timezone.now()
    delivery.last_error = ""
    delivery.save(update_fields=(
        "status",
        "sent_at",
        "last_error",
        "updated_at",
    ))
