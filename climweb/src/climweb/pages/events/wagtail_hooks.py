from django.db import transaction
from loguru import logger
from wagtail import hooks

from .models import EventPage


@hooks.register("after_publish_page")
def enqueue_google_meet_sync(request, page):
    """Synchronize Google Meet only after the new page revision is committed."""

    if not isinstance(page.specific, EventPage):
        return

    event = page.specific
    if not event.uses_google_meet:
        return

    event_id = event.pk

    def enqueue():
        from .tasks import sync_google_meet_event_task

        try:
            sync_google_meet_event_task.delay(event_id)
        except Exception as exc:
            # Publishing must remain successful even if the broker is briefly
            # unavailable. The failure is visible in logs and can be retried by
            # publishing again; Phase 2 adds an explicit admin retry action.
            logger.error(
                f"[GOOGLE_MEET] Could not enqueue event sync for {event_id}: {exc}"
            )

    transaction.on_commit(enqueue)
