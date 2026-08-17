from html import escape
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from django.db import transaction
from django.template.loader import render_to_string
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


def _get_email_context():
    context = {
        "site_name": "ACMAD",
        "logo_url": None,
        "theme": {
            'text_color': '#363636',
            'primary_color': '#0C447C',
            'background_color': '#F4F6F8',
            'border_radius': '8px',
        },
        "social_media": [],
    }
    
    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        return context
        
    context["site_name"] = site.site_name
    
    try:
        from climweb.base.models import Theme, OrganisationSetting
        from climweb.base.utils import mix_with_white
        
        d_theme = Theme.objects.filter(is_default=True).first()
        if d_theme:
            context["theme"] = {
                'primary_color': d_theme.primary_hover_color,
                'text_color': d_theme.primary_color,
                'background_color': mix_with_white(d_theme.primary_hover_color, 0.8),
                'border_radius': f"{d_theme.border_radius * 0.06}em",
            }
            
        org = OrganisationSetting.for_site(site)
        if org.logo:
            logo_url = org.logo.get_rendition("max-200x100").url
            context["logo_url"] = f"{site.root_url.rstrip('/')}{logo_url}"
            
        if org.social_media_accounts:
            context["social_media"] = [
                {"name": block.value.get("name"), "url": block.value.get("full_url")}
                for block in org.social_media_accounts
                if block.value.get("full_url")
            ]
    except Exception:
        pass
        
    return context


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
    
    context = _get_email_context()
    context.update({"confirmation_url": confirmation_url})
    
    text = (
        "Confirm your ACMAD product subscription by opening this link:\n\n"
        f"{confirmation_url}\n\n"
        "If you did not request this subscription, ignore this email."
    )
    
    html = render_to_string("products/email/subscription_confirm.html", context)
    
    send_mail(
        "Confirm your ACMAD product subscription",
        text,
        [subscriber.email],
        html_message=html,
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
        
        context = _get_email_context()
        context.update({
            "product_label": product_label,
            "source_published_date": source_import.source_published_date,
            "filename": filename,
            "product_url": product_url,
            "preferences_url": preferences_url,
            "unsubscribe_url": unsubscribe_url,
        })
        
        html = render_to_string("products/email/product_notification.html", context)
        
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
