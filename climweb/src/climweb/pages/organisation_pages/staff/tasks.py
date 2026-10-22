import mimetypes
from types import SimpleNamespace
from datetime import timedelta

from celery.schedules import crontab
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from climweb.config.celery import app

from .google_drive import drive_is_configured, ensure_staff_folder, get_drive_service, record_audit, upload_file
from .models import StaffDriveAudit, StaffNotificationDelivery, StaffTrainingReportDocument
from .notifications import queue_deadline_notifications, send_staff_notification


@app.task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=4)
def deliver_staff_notification(delivery_id):
    return send_staff_notification(delivery_id)


@app.task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=4)
def sync_report_document_to_drive(document_id, actor_id=None):
    document = StaffTrainingReportDocument.objects.select_related("report__assignment__member").get(pk=document_id)
    if document.drive_file_id:
        return document.drive_file_id
    if not drive_is_configured():
        document.drive_sync_status = StaffTrainingReportDocument.DriveSyncStatus.DISABLED
        document.drive_sync_error = "Google Drive is disabled."
        document.save(update_fields=["drive_sync_status", "drive_sync_error"])
        return ""
    try:
        service = get_drive_service()
        member = document.report.assignment.member
        actor = get_user_model().objects.filter(pk=actor_id).first() if actor_id else None
        folder_id = ensure_staff_folder(service, member, actor)
        with document.file.open("rb") as source:
            upload = SimpleNamespace(
                file=source,
                name=document.original_name,
                content_type=mimetypes.guess_type(document.original_name)[0] or "application/octet-stream",
            )
            item = upload_file(service, folder_id, upload)
        record_audit(
            actor,
            member,
            StaffDriveAudit.Action.FILE_UPLOADED,
            item,
            parent_id=folder_id,
            source="activity_report",
            report_id=document.report_id,
            document_id=document.pk,
        )
    except Exception as exc:
        StaffTrainingReportDocument.objects.filter(pk=document.pk).update(
            drive_sync_status=StaffTrainingReportDocument.DriveSyncStatus.FAILED,
            drive_sync_error=str(exc)[:1000],
        )
        raise
    StaffTrainingReportDocument.objects.filter(pk=document.pk).update(
        drive_file_id=item["id"],
        drive_sync_status=StaffTrainingReportDocument.DriveSyncStatus.SYNCED,
        drive_sync_error="",
        drive_synced_at=timezone.now(),
    )
    return item["id"]


def queue_report_document_drive_sync(documents, actor):
    if not documents:
        return
    actor_id = actor.pk if actor and actor.is_authenticated else None
    document_ids = [document.pk for document in documents]

    def dispatch():
        for document_id in document_ids:
            try:
                sync_report_document_to_drive.delay(document_id, actor_id)
            except Exception:
                # A periodic recovery task will enqueue pending documents when
                # the broker becomes available again.
                continue

    transaction.on_commit(dispatch)


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


@app.task
def recover_report_document_drive_syncs():
    document_ids = list(
        StaffTrainingReportDocument.objects.filter(
            drive_file_id="",
            drive_sync_status__in=[
                StaffTrainingReportDocument.DriveSyncStatus.PENDING,
                StaffTrainingReportDocument.DriveSyncStatus.FAILED,
            ],
            uploaded_at__lt=timezone.now() - timedelta(minutes=5),
        ).values_list("pk", flat=True)[:100]
    )
    for document_id in document_ids:
        sync_report_document_to_drive.delay(document_id)
    return len(document_ids)


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
    sender.add_periodic_task(
        crontab(minute="*/15"),
        recover_report_document_drive_syncs.s(),
        name="recover-staff-report-drive-syncs",
    )
