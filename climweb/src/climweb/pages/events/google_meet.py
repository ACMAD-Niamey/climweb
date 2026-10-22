"""Google Calendar-backed Meet integration for ClimWeb events."""

import hashlib
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.html import strip_tags
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import EventMeeting, GoogleMeetSettings


CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleMeetConfigurationError(ImproperlyConfigured):
    pass


class GoogleMeetConferencePending(RuntimeError):
    pass


def deterministic_calendar_event_id(event):
    """Return a Google-compatible, stable ID so retries cannot create duplicates."""

    site = event.get_site()
    identity = f"climweb:{site.hostname}:{site.pk}:{event.pk}".encode("utf-8")
    return "c" + hashlib.sha256(identity).hexdigest()[:48]


def get_google_meet_settings(event):
    site = event.get_site()
    if site is None:
        raise GoogleMeetConfigurationError("The event is not attached to a Wagtail site.")

    integration_settings = GoogleMeetSettings.for_site(site)
    if not integration_settings.enabled:
        raise GoogleMeetConfigurationError(
            "Google Meet integration is disabled for this site."
        )
    if not integration_settings.organizer_email:
        raise GoogleMeetConfigurationError(
            "A Google Workspace organizer email has not been configured."
        )
    return integration_settings


def get_calendar_service(organizer_email):
    credentials_file = getattr(settings, "GOOGLE_MEET_SERVICE_ACCOUNT_FILE", "")
    if not credentials_file:
        raise GoogleMeetConfigurationError(
            "GOOGLE_MEET_SERVICE_ACCOUNT_FILE is not configured."
        )
    if not Path(credentials_file).is_file():
        raise GoogleMeetConfigurationError(
            "GOOGLE_MEET_SERVICE_ACCOUNT_FILE does not point to a readable file."
        )

    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=[CALENDAR_EVENTS_SCOPE],
    ).with_subject(organizer_email)
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def build_calendar_event_body(event, meeting, include_conference=False):
    if not event.date_to:
        raise GoogleMeetConfigurationError(
            "Online and hybrid events require an end date and time."
        )

    description = strip_tags(str(event.description)).strip()
    if event.full_url:
        description = f"{description}\n\nEvent details: {event.full_url}".strip()

    event_timezone = event.timezone
    start_at = timezone.localtime(event.date_from, event_timezone)
    end_at = timezone.localtime(event.date_to, event_timezone)

    body = {
        "id": meeting.calendar_event_id,
        "summary": event.title,
        "description": description,
        "start": {
            "dateTime": start_at.isoformat(),
            "timeZone": str(event_timezone),
        },
        "end": {
            "dateTime": end_at.isoformat(),
            "timeZone": str(event_timezone),
        },
        "extendedProperties": {
            "private": {
                "climweb_event_page_id": str(event.pk),
            }
        },
    }
    if event.location:
        body["location"] = event.location
    if include_conference:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": str(meeting.conference_request_id),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
    return body


def calendar_payload_hash(body):
    comparable = {key: value for key, value in body.items() if key != "id"}
    return hashlib.sha256(
        json.dumps(comparable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def extract_meet_url(calendar_event):
    if calendar_event.get("hangoutLink"):
        return calendar_event["hangoutLink"]

    for entry_point in calendar_event.get("conferenceData", {}).get("entryPoints", []):
        if entry_point.get("entryPointType") == "video" and entry_point.get("uri"):
            return entry_point["uri"]
    return ""


def _http_status(exc):
    return getattr(getattr(exc, "resp", None), "status", None)


def sync_google_meet_event(event, force_remote_check=False):
    """Create or update one Calendar event and return its operational record."""

    if not event.uses_google_meet:
        raise GoogleMeetConfigurationError("This event is not configured for Google Meet.")

    integration_settings = get_google_meet_settings(event)
    meeting, _ = EventMeeting.objects.get_or_create(
        event=event,
        defaults={"calendar_event_id": deterministic_calendar_event_id(event)},
    )

    base_body = build_calendar_event_body(event, meeting)
    payload_hash = calendar_payload_hash(base_body)
    if (
        meeting.sync_status == EventMeeting.SyncStatus.READY
        and meeting.meet_url
        and meeting.payload_hash == payload_hash
        and not force_remote_check
    ):
        return meeting

    meeting.sync_status = EventMeeting.SyncStatus.SYNCING
    meeting.last_error = ""
    meeting.save(update_fields=("sync_status", "last_error", "updated_at"))

    calendar_id = integration_settings.calendar_id or "primary"
    service = get_calendar_service(integration_settings.organizer_email)

    try:
        remote_event = service.events().get(
            calendarId=calendar_id,
            eventId=meeting.calendar_event_id,
        ).execute()
    except HttpError as exc:
        if _http_status(exc) != 404:
            raise
        remote_event = None

    if remote_event is None:
        if meeting.last_synced_at:
            # The remote event was deliberately deleted after a previous
            # successful sync. A new conference must use a fresh request ID;
            # retrying a timed-out first creation still keeps the original ID.
            meeting.conference_request_id = uuid.uuid4()
            meeting.save(update_fields=("conference_request_id", "updated_at"))
        create_body = build_calendar_event_body(
            event,
            meeting,
            include_conference=True,
        )
        try:
            remote_event = service.events().insert(
                calendarId=calendar_id,
                body=create_body,
                conferenceDataVersion=1,
                sendUpdates="none",
            ).execute()
        except HttpError as exc:
            if _http_status(exc) != 409:
                raise
            remote_event = service.events().get(
                calendarId=calendar_id,
                eventId=meeting.calendar_event_id,
            ).execute()
    elif meeting.payload_hash != payload_hash:
        # PATCH preserves conferenceData because it is intentionally omitted.
        patch_body = dict(base_body)
        patch_body.pop("id", None)
        remote_event = service.events().patch(
            calendarId=calendar_id,
            eventId=meeting.calendar_event_id,
            body=patch_body,
            conferenceDataVersion=1,
            sendUpdates="none",
        ).execute()

    meet_url = extract_meet_url(remote_event)
    meeting.payload_hash = payload_hash
    meeting.meet_url = meet_url
    meeting.last_synced_at = timezone.now()
    meeting.sync_status = (
        EventMeeting.SyncStatus.READY
        if meet_url
        else EventMeeting.SyncStatus.PENDING
    )
    meeting.save(update_fields=(
        "payload_hash",
        "meet_url",
        "last_synced_at",
        "sync_status",
        "updated_at",
    ))

    if not meet_url:
        raise GoogleMeetConferencePending(
            "Google Calendar is still generating the Meet conference."
        )
    return meeting
