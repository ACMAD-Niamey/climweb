from datetime import timedelta

from celery.schedules import crontab
from django.utils import timezone

from climweb.config.celery import app

from .models import StaffNotificationDelivery
from .notifications import queue_deadline_notifications, send_staff_notification


@app.task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=4)
def deliver_staff_notification(delivery_id):
    return send_staff_notification(delivery_id)


@app.task
def send_staff_deadline_reminders():
    return queue_deadline_notifications()


@app.task
def recover_staff_notifications():
    cutoff = timezone.now() - timedelta(minutes=15)
    delivery_ids = list(
        StaffNotificationDelivery.objects.filter(
            status__in=[StaffNotificationDelivery.Status.PENDING, StaffNotificationDelivery.Status.FAILED],
            attempts__lt=5,
            created_at__lt=cutoff,
        ).values_list("pk", flat=True)[:100]
    )
    for delivery_id in delivery_ids:
        deliver_staff_notification.delay(delivery_id)
    return len(delivery_ids)


@app.on_after_finalize.connect
def setup_staff_notification_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=7, minute=0),
        send_staff_deadline_reminders.s(),
        name="send-staff-report-deadline-reminders-daily",
    )
    sender.add_periodic_task(
        crontab(minute=15),
        recover_staff_notifications.s(),
        name="recover-pending-staff-notifications-hourly",
    )
