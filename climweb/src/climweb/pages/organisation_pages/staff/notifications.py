import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Site

from climweb.base.mail import send_mail

from .models import StaffEmployment, StaffNotificationDelivery, StaffTrainingAssignment, StaffTrainingReport


logger = logging.getLogger(__name__)


def _absolute_url(path):
    base_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "").rstrip("/")
    if not base_url:
        site = Site.objects.filter(is_default_site=True).first()
        base_url = site.root_url.rstrip("/") if site else ""
    return f"{base_url}{path}" if base_url else path


def _email_logo_url():
    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        return ""
    try:
        from climweb.base.models import OrganisationSetting

        organisation = OrganisationSetting.for_site(site)
        logo = organisation.logo or organisation.cms_logo
        if not logo:
            return ""
        url = str(logo.get_rendition("max-220x100").url)
        if url.startswith(("http://", "https://", "//")):
            return url
        return f"{site.root_url.rstrip('/')}/{url.lstrip('/')}"
    except Exception:
        logger.exception("Could not prepare the organisation logo for staff email")
        return ""


def _staff_email(assignment):
    try:
        user = assignment.member.profile_access.user
    except (AttributeError, ObjectDoesNotExist):
        return ""
    return user.email.strip().lower() if user.is_active and user.email else ""


def _reviewer_emails():
    User = get_user_model()
    return list(
        User.objects.filter(is_active=True)
        .exclude(email="")
        .filter(
            Q(is_superuser=True)
            | Q(user_permissions__content_type__app_label="staff", user_permissions__codename="review_staff_profiles")
            | Q(groups__permissions__content_type__app_label="staff", groups__permissions__codename="review_staff_profiles")
        )
        .values_list("email", flat=True)
        .distinct()
    )


def _dispatch_safely(delivery_id):
    try:
        from .tasks import deliver_staff_notification

        deliver_staff_notification.delay(delivery_id)
    except Exception:
        # The pending row remains available to the hourly recovery task if the
        # broker is temporarily unavailable.
        logger.exception("Could not enqueue staff notification %s", delivery_id)


def _queue(event, assignment, recipient, *, report=None, marker=""):
    recipient = (recipient or "").strip().lower()
    if not recipient:
        return None, False
    raw_key = f"{event}|{assignment.pk}|{report.pk if report else ''}|{recipient}|{marker}"
    delivery, created = StaffNotificationDelivery.objects.get_or_create(
        dedupe_key=hashlib.sha256(raw_key.encode()).hexdigest(),
        defaults={
            "event": event,
            "assignment": assignment,
            "report": report,
            "recipient": recipient,
        },
    )
    if created:
        transaction.on_commit(lambda delivery_id=delivery.pk: _dispatch_safely(delivery_id))
    return delivery, created


def queue_training_assigned_notifications(assignments):
    deliveries = []
    for assignment in assignments:
        if assignment.status in [StaffTrainingAssignment.Status.CANCELLED, StaffTrainingAssignment.Status.COMPLETED]:
            continue
        delivery, _ = _queue(
            StaffNotificationDelivery.Event.TRAINING_ASSIGNED,
            assignment,
            _staff_email(assignment),
        )
        if delivery:
            deliveries.append(delivery)
    return deliveries


def queue_nomination_removed_notification(assignment):
    delivery, _ = _queue(
        StaffNotificationDelivery.Event.ACTIVITY_NOMINATION_REMOVED,
        assignment,
        _staff_email(assignment),
    )
    return delivery


def queue_report_submitted_notifications(report):
    marker = report.submitted_at.isoformat() if report.submitted_at else str(report.updated_at)
    deliveries = []
    for recipient in _reviewer_emails():
        delivery, _ = _queue(
            StaffNotificationDelivery.Event.REPORT_SUBMITTED,
            report.assignment,
            recipient,
            report=report,
            marker=marker,
        )
        if delivery:
            deliveries.append(delivery)
    return deliveries


def queue_report_reviewed_notification(report):
    event = (
        StaffNotificationDelivery.Event.REPORT_APPROVED
        if report.status == StaffTrainingReport.Status.APPROVED
        else StaffNotificationDelivery.Event.REPORT_CHANGES_REQUESTED
    )
    marker = report.reviewed_at.isoformat() if report.reviewed_at else str(report.updated_at)
    delivery, _ = _queue(
        event,
        report.assignment,
        _staff_email(report.assignment),
        report=report,
        marker=marker,
    )
    return delivery


def queue_deadline_notifications(today=None):
    today = today or timezone.localdate()
    actionable = StaffTrainingAssignment.objects.exclude(
        status__in=[StaffTrainingAssignment.Status.CANCELLED, StaffTrainingAssignment.Status.COMPLETED]
    ).exclude(
        member__employment__status__in=[StaffEmployment.Status.RETIRED, StaffEmployment.Status.LEFT]
    ).filter(
        Q(report__isnull=True)
        | Q(report__status__in=[StaffTrainingReport.Status.DRAFT, StaffTrainingReport.Status.CHANGES_REQUESTED])
    ).select_related("member__profile_access__user", "report")

    events_by_days = {
        7: StaffNotificationDelivery.Event.REPORT_DUE_7_DAYS,
        3: StaffNotificationDelivery.Event.REPORT_DUE_3_DAYS,
        1: StaffNotificationDelivery.Event.REPORT_DUE_1_DAY,
    }
    created_count = 0
    for days, event in events_by_days.items():
        for assignment in actionable.filter(report_due_date=today + timedelta(days=days)):
            _, created = _queue(event, assignment, _staff_email(assignment), marker=str(today))
            created_count += int(created)

    # Overdue mail is sent on the first overdue day and then weekly, avoiding
    # noisy daily messages while still escalating unresolved reports.
    for assignment in actionable.filter(report_due_date__lt=today):
        days_overdue = (today - assignment.report_due_date).days
        if days_overdue % 7 != 1:
            continue
        _, created = _queue(
            StaffNotificationDelivery.Event.REPORT_OVERDUE,
            assignment,
            _staff_email(assignment),
            marker=str(today),
        )
        created_count += int(created)
    return created_count


def _message_context(delivery):
    assignment = delivery.assignment
    report = delivery.report
    event = delivery.event
    staff_report_url = _absolute_url(reverse("staff_portal:training_report", args=[assignment.pk]))
    details = [
        {"label": "Activity", "value": assignment.title},
        {"label": "Type", "value": assignment.get_activity_type_display()},
        {"label": "Dates", "value": f"{assignment.start_date:%d %B %Y} – {assignment.end_date:%d %B %Y}"},
    ]
    if assignment.organizer:
        details.append({"label": "Organizer", "value": assignment.organizer})
    if assignment.location:
        details.append({"label": "Location", "value": assignment.location})
    if assignment.report_due_date:
        details.append({"label": "Report deadline", "value": f"{assignment.report_due_date:%d %B %Y}"})

    context = {
        "greeting": f"Hello {assignment.member.name},",
        "details": details,
        "comment": "",
        "logo_url": _email_logo_url(),
        "action_url": staff_report_url,
        "action_label": "Open staff dashboard",
    }
    if event == StaffNotificationDelivery.Event.TRAINING_ASSIGNED:
        context.update(
            subject=f"Activity assignment: {assignment.title}",
            headline="You have been assigned a professional activity",
            message="HR has nominated you for the activity below. Please review the details and submit your report after the activity.",
        )
    elif event == StaffNotificationDelivery.Event.ACTIVITY_NOMINATION_REMOVED:
        context.update(
            subject=f"Activity nomination removed: {assignment.title}",
            headline="Your activity nomination has been removed",
            message="HR has removed your nomination for the activity below. You are no longer expected to attend or submit a report for this activity.",
            action_url=_absolute_url(reverse("staff_portal:dashboard")),
        )
    elif event == StaffNotificationDelivery.Event.REPORT_SUBMITTED:
        context.update(
            greeting="Hello HR team,",
            subject=f"Activity report awaiting review: {assignment.member.name}",
            headline="An activity report is awaiting review",
            message=f"{assignment.member.name} submitted a report for {assignment.title}.",
            action_url=_absolute_url(reverse("staff_portal:hr_review_training_report", args=[report.pk])),
            action_label="Review report",
        )
    elif event == StaffNotificationDelivery.Event.REPORT_APPROVED:
        context.update(
            subject=f"Activity report approved: {assignment.title}",
            headline="Your activity report has been approved",
            message="HR has approved your activity report.",
            comment=report.reviewer_comment,
        )
    elif event == StaffNotificationDelivery.Event.REPORT_CHANGES_REQUESTED:
        context.update(
            subject=f"Changes requested: {assignment.title}",
            headline="HR requested changes to your activity report",
            message="Please review the feedback, update the report and submit it again.",
            comment=report.reviewer_comment,
            action_label="Update report",
        )
    else:
        if event == StaffNotificationDelivery.Event.REPORT_OVERDUE:
            headline = "Your activity report is overdue"
            message = "Please submit the report as soon as possible. Contact HR if the deadline needs to be reviewed."
            subject = f"Overdue activity report: {assignment.title}"
        else:
            days = {
                StaffNotificationDelivery.Event.REPORT_DUE_7_DAYS: 7,
                StaffNotificationDelivery.Event.REPORT_DUE_3_DAYS: 3,
                StaffNotificationDelivery.Event.REPORT_DUE_1_DAY: 1,
            }[event]
            headline = f"Your activity report is due in {days} day{'s' if days != 1 else ''}"
            message = "Please complete and submit your report before the deadline."
            subject = f"Activity report due in {days} day{'s' if days != 1 else ''}: {assignment.title}"
        context.update(subject=subject, headline=headline, message=message, action_label="Open report")
    return context


def send_staff_notification(delivery_id):
    error = None
    with transaction.atomic():
        delivery = (
            StaffNotificationDelivery.objects.select_for_update(of=("self",))
            .select_related("assignment__member", "assignment__member__profile_access__user", "report")
            .get(pk=delivery_id)
        )
        if delivery.status == StaffNotificationDelivery.Status.SENT:
            return False
        context = _message_context(delivery)
        try:
            sent = send_mail(
                context["subject"],
                render_to_string("staff/email/workflow_notification.txt", context),
                [delivery.recipient],
                html_message=render_to_string("staff/email/workflow_notification.html", context),
                fail_silently=False,
            )
            if not sent:
                raise RuntimeError("The email backend reported that no message was sent.")
        except Exception as exc:
            delivery.status = StaffNotificationDelivery.Status.FAILED
            delivery.last_error = str(exc)[:2000]
            error = exc
        else:
            delivery.status = StaffNotificationDelivery.Status.SENT
            delivery.sent_at = timezone.now()
            delivery.last_error = ""
        delivery.attempts += 1
        delivery.save(update_fields=["status", "sent_at", "last_error", "attempts"])
    if error:
        raise error
    return True
