from html import escape
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Site

from climweb.base.mail import send_mail

from .import_registry import get_product_import_definition
from .models import (
    ProductNotificationDelivery,
    ProductNotificationEvent,
    ProductSourceImport,
    ProductSubscriber,
)


def _public_url(path):
    site = Site.objects.filter(is_default_site=True).first()
    return f"{site.root_url.rstrip('/')}{path}" if site else path


def _source_filename(source_import):
    return unquote(PurePosixPath(urlsplit(source_import.source_url).path).name)


def _product_url(source_import):
    if source_import.product_item_page_id:
        return _public_url(source_import.product_item_page.url)
    return source_import.source_url


def queue_automatic_product_notifications(product_family, started_at):
    """Queue successful records touched by one automatic importer execution."""
    definition = get_product_import_definition(product_family)
    if definition is None:
        return []

    source_imports = ProductSourceImport.objects.filter(
        product__name__in=definition["product_names"],
        status=ProductSourceImport.STATUS_IMPORTED,
        updated_at__gte=started_at,
    ).order_by("source_published_date", "pk")

    event_ids = []
    for source_import in source_imports:
        event, created = ProductNotificationEvent.objects.get_or_create(
            automatic_key=f"automatic:{source_import.pk}",
            defaults={
                "product_family": product_family,
                "source_import": source_import,
                "trigger": ProductNotificationEvent.TRIGGER_AUTOMATIC,
            },
        )
        if created:
            event_ids.append(event.pk)

    if event_ids:
        from .tasks import send_product_notification

        transaction.on_commit(
            lambda: [send_product_notification.delay(event_id) for event_id in event_ids]
        )
    return event_ids


def queue_latest_product_notification(product_family, requested_by):
    definition = get_product_import_definition(product_family)
    if definition is None:
        return None
    source_import = (
        ProductSourceImport.objects.filter(
            product__name__in=definition["product_names"],
            status=ProductSourceImport.STATUS_IMPORTED,
        )
        .order_by("-source_published_date", "-imported_at")
        .first()
    )
    if source_import is None:
        return None

    event = ProductNotificationEvent.objects.create(
        product_family=product_family,
        source_import=source_import,
        trigger=ProductNotificationEvent.TRIGGER_MANUAL,
        requested_by=requested_by,
    )
    from .tasks import send_product_notification

    transaction.on_commit(lambda: send_product_notification.delay(event.pk))
    return event


def send_confirmation_email(subscriber):
    confirmation_url = _public_url(
        reverse(
            "product_subscription_confirm",
            kwargs={"token": subscriber.confirmation_token},
        )
    )
    send_mail(
        "Confirm your ACMAD product subscription",
        (
            "Confirm your ACMAD product subscription by opening this link:\n\n"
            f"{confirmation_url}\n\n"
            "If you did not request this subscription, ignore this email."
        ),
        [subscriber.email],
    )


def deliver_product_notification(event_id):
    event = ProductNotificationEvent.objects.select_related(
        "source_import__product", "source_import__product_item_page"
    ).get(pk=event_id)
    if event.status == ProductNotificationEvent.STATUS_SENT:
        return event

    event.status = ProductNotificationEvent.STATUS_SENDING
    event.error_message = ""
    event.save(update_fields=["status", "error_message"])

    subscribers = ProductSubscriber.objects.filter(
        status=ProductSubscriber.STATUS_ACTIVE,
        preferences__product_family=event.product_family,
    ).distinct()
    event.recipient_count = subscribers.count()
    event.save(update_fields=["recipient_count"])

    source_import = event.source_import
    definition = get_product_import_definition(event.product_family) or {}
    product_label = definition.get("label", source_import.product.name)
    product_url = _product_url(source_import)
    filename = _source_filename(source_import)
    subject = f"New ACMAD product: {product_label} — {source_import.source_published_date}"

    sent_count = 0
    failed_count = 0
    errors = []
    for subscriber in subscribers:
        delivery, _ = ProductNotificationDelivery.objects.get_or_create(
            event=event, subscriber=subscriber
        )
        if delivery.status == ProductNotificationDelivery.STATUS_SENT:
            sent_count += 1
            continue
        preferences_url = _public_url(
            reverse(
                "product_subscription_preferences",
                kwargs={"token": subscriber.unsubscribe_token},
            )
        )
        unsubscribe_url = _public_url(
            reverse(
                "product_subscription_unsubscribe",
                kwargs={"token": subscriber.unsubscribe_token},
            )
        )
        text = (
            f"A new {product_label} product is available.\n\n"
            f"Issue date: {source_import.source_published_date}\n"
            f"File: {filename}\n"
            f"View product: {product_url}\n\n"
            f"Manage preferences: {preferences_url}\n"
            f"Unsubscribe: {unsubscribe_url}"
        )
        html = (
            f"<h2>{escape(product_label)}</h2>"
            f"<p>A new ACMAD product is available for "
            f"<strong>{escape(str(source_import.source_published_date))}</strong>.</p>"
            f"<p><a href=\"{escape(product_url)}\">View {escape(filename)}</a></p>"
            f"<p><a href=\"{escape(preferences_url)}\">Manage preferences</a> · "
            f"<a href=\"{escape(unsubscribe_url)}\">Unsubscribe</a></p>"
        )
        try:
            send_mail(subject, text, [subscriber.email], html_message=html)
        except Exception as exc:
            failed_count += 1
            delivery.status = ProductNotificationDelivery.STATUS_FAILED
            delivery.error_message = str(exc)
            errors.append(f"{subscriber.email}: {exc}")
        else:
            sent_count += 1
            delivery.status = ProductNotificationDelivery.STATUS_SENT
            delivery.error_message = ""
            delivery.sent_at = timezone.now()
        delivery.save()

    event.sent_count = sent_count
    event.failed_count = failed_count
    event.finished_at = timezone.now()
    event.status = (
        ProductNotificationEvent.STATUS_FAILED
        if failed_count
        else ProductNotificationEvent.STATUS_SENT
    )
    event.error_message = "\n".join(errors)[:10000]
    event.save(
        update_fields=[
            "sent_count",
            "failed_count",
            "finished_at",
            "status",
            "error_message",
        ]
    )
    return event
