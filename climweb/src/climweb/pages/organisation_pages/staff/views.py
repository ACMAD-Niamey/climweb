import hashlib
import logging
from functools import wraps

from django.contrib import messages
from django.conf import settings
from django.contrib.auth import logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    StaffAuthenticationForm,
    StaffCreateForm,
    StaffEditForm,
    StaffInvitationForm,
    StaffLinkUserForm,
    StaffOffboardingForm,
    StaffPasswordResetForm,
    StaffProfileForm,
    StaffReactivationForm,
    StaffReviewForm,
    StaffTrainingAssignmentForm,
    StaffTrainingReportForm,
    StaffTrainingReportReviewForm,
)
from .models import (
    StaffEmploymentEvent,
    StaffMember,
    StaffProfileAccess,
    StaffProfileUpdate,
    StaffTrainingAssignment,
    StaffTrainingReport,
    StaffTrainingReportDocument,
)
from .notifications import queue_report_submitted_notifications, queue_training_assigned_notifications
from .services import (
    change_staff_employment,
    create_staff_member,
    edit_staff_member,
    invitation_valid,
    invite_staff,
    link_existing_staff_user,
    member_fingerprint,
    review_training_report_submission,
    review_update,
    send_profile_update_reminder,
)

logger = logging.getLogger(__name__)


class StaffLoginView(LoginView):
    template_name = "staff/portal/login.html"
    authentication_form = StaffAuthenticationForm
    next_page = reverse_lazy("staff_portal:profile")

    def get_success_url(self):
        # Do not accept a next URL into the wider dashboard.
        return str(self.next_page)


class StaffPasswordResetView(PasswordResetView):
    form_class = StaffPasswordResetForm
    template_name = "staff/portal/password_reset.html"
    email_template_name = "staff/portal/password_reset_email.txt"
    subject_template_name = "staff/portal/password_reset_subject.txt"
    success_url = reverse_lazy("staff_portal:password_reset_done")

    def form_valid(self, form):
        # Generic success response prevents account enumeration; bound email
        # delivery per address and per client to limit reset-email abuse.
        values = ["email:" + form.cleaned_data["email"].lower(), "ip:" + self.request.META.get("REMOTE_ADDR", "")]
        for value in values:
            key = "staff-password-reset:" + hashlib.sha256(value.encode()).hexdigest()
            if cache.add(key, 1, timeout=900):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=900)
                    count = 1
            if count > 5:
                return redirect(self.success_url)
        return super().form_valid(form)


@never_cache
@require_http_methods(["GET", "POST"])
def staff_logout(request):
    """Offer a safe direct logout URL while keeping session changes POST-only."""
    if request.method == "POST":
        auth_logout(request)
        return redirect("staff_portal:login")
    return render(request, "staff/portal/logout_confirm.html")


class StaffPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "staff/portal/password_reset_confirm.html"
    success_url = reverse_lazy("staff_portal:login")

    def get_user(self, uidb64):
        user = super().get_user(uidb64)
        if user and user.is_active and hasattr(user, "staff_profile_access") and user.staff_profile_access.member.is_current_staff:
            return user
        return None


def staff_required(view):
    @login_required(login_url="staff_portal:login")
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        request.staff_access = get_object_or_404(
            StaffProfileAccess.objects.select_related("member__department", "member__photo", "user"),
            user=request.user,
        )
        if not request.staff_access.member.is_current_staff:
            raise PermissionDenied("This staff profile is no longer active.")
        return view(request, *args, **kwargs)
    return never_cache(wrapped)


def reviewer_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active or not request.user.has_perm("staff.review_staff_profiles"):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return never_cache(wrapped)


@never_cache
@require_http_methods(["GET", "POST"])
def accept_invitation(request, access_id, token):
    with transaction.atomic():
        member_id = get_object_or_404(StaffProfileAccess, pk=access_id).member_id
        StaffMember.objects.select_for_update().get(pk=member_id)
        access = get_object_or_404(StaffProfileAccess.objects.select_for_update().select_related("user"), pk=access_id)
        valid = invitation_valid(access, token)
        form = SetPasswordForm(access.user, request.POST or None) if valid else None
        if request.method == "POST" and valid and form.is_valid():
            form.save()
            access.accepted_at = timezone.now()
            access.invitation_digest = ""
            access.save(update_fields=["accepted_at", "invitation_digest"])
            messages.success(request, "Your password is set. Sign in using your work email address.")
            response = redirect("staff_portal:login")
        else:
            response = render(request, "staff/portal/accept.html", {"form": form, "valid": valid}, status=200 if valid else 400)
    # Keep invitation URLs private off-site without suppressing the Origin
    # header on same-origin form POSTs (which Django's CSRF checks require).
    response["Referrer-Policy"] = "same-origin"
    return response


def profile_initial(member, update):
    if update:
        return {"biography": update.biography, "website": update.website, "linkedin": update.linkedin,
                "github": update.github, "publications": update.publications}
    return {
        "biography": strip_tags((member.bio or "").replace("</p>", "\n\n")).strip(),
        "website": member.website,
        "linkedin": member.linkedin,
        "github": member.github,
        "publications": member.publications,
    }


@staff_required
@require_http_methods(["GET"])
def staff_dashboard(request):
    assignments = StaffTrainingAssignment.objects.filter(member=request.staff_access.member).select_related("report")
    open_assignments = assignments.exclude(status=StaffTrainingAssignment.Status.CANCELLED)
    return render(request, "staff/portal/dashboard.html", {
        "member": request.staff_access.member,
        "assignments": assignments[:6],
        "training_count": open_assignments.count(),
        "reports_due": open_assignments.filter(
            Q(report__isnull=True) | Q(report__status__in=[StaffTrainingReport.Status.DRAFT, StaffTrainingReport.Status.CHANGES_REQUESTED])
        ).count(),
        "approved_count": assignments.filter(report__status=StaffTrainingReport.Status.APPROVED).count(),
        "drive_url": getattr(settings, "STAFF_GOOGLE_DRIVE_URL", ""),
    })


@staff_required
@reviewer_required
@require_http_methods(["GET"])
def staff_hr_dashboard(request):
    assignments = StaffTrainingAssignment.objects.select_related("member", "report", "assigned_by")
    submitted_reports = StaffTrainingReport.objects.filter(
        status=StaffTrainingReport.Status.SUBMITTED,
    ).select_related("assignment__member")
    return render(request, "staff/portal/hr_dashboard.html", {
        "training_assignments": assignments[:50],
        "submitted_reports": submitted_reports,
        "assignment_count": assignments.count(),
        "awaiting_review_count": submitted_reports.count(),
        "approved_count": StaffTrainingReport.objects.filter(status=StaffTrainingReport.Status.APPROVED).count(),
    })


@staff_required
@reviewer_required
@require_http_methods(["GET", "POST"])
def staff_hr_assign_training(request):
    form = StaffTrainingAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            assignments = form.save(request.user)
            queue_training_assigned_notifications(assignments)
        messages.success(request, f"{len(assignments)} staff member(s) were assigned to {assignments[0].title}.")
        return redirect("staff_portal:hr_dashboard")
    return render(request, "staff/portal/hr_assign_training.html", {"form": form})


@staff_required
@reviewer_required
@require_http_methods(["GET", "POST"])
def staff_hr_review_training_report(request, report_id):
    report = get_object_or_404(StaffTrainingReport.objects.select_related("assignment__member"), pk=report_id)
    form = StaffTrainingReportReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            report, message = review_training_report_submission(
                report.pk,
                request.user,
                form.cleaned_data["action"],
                form.cleaned_data["comment"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, message)
            return redirect("staff_portal:hr_dashboard")
    return render(request, "staff/portal/hr_review_training_report.html", {"report": report, "form": form})


@staff_required
@require_http_methods(["GET", "POST"])
def profile(request):
    access = request.staff_access
    with transaction.atomic():
        member = StaffMember.objects.select_for_update().get(pk=access.member_id)
        if not member.is_current_staff:
            raise PermissionDenied("This staff profile is no longer active.")
        # Serializes draft creation/submission for this account, including two tabs.
        access = StaffProfileAccess.objects.select_for_update(of=("self",)).select_related("member__department", "user").get(pk=access.pk)
        update = access.updates.filter(status__in=["draft", "submitted"]).first()
        submitted = bool(update and update.status == "submitted")
        previous = update or access.updates.first()
        initial = profile_initial(access.member, previous if previous and previous.status != "approved" else None)
        form = StaffProfileForm(request.POST if request.method == "POST" else None, request.FILES or None, initial=initial)
        if request.method == "POST":
            action = request.POST.get("action")
            if submitted:
                messages.error(request, "Your submission is awaiting review. It cannot be edited until the reviewer responds.")
                return redirect("staff_portal:profile")
            if action not in {"save", "submit"}:
                return HttpResponse("Unknown action", status=400)
            if form.is_valid():
                if not update:
                    update = StaffProfileUpdate(access=access, source_fingerprint=member_fingerprint(access.member))
                    if previous and previous.status == "changes_requested":
                        update.photo_data = previous.photo_data
                update.biography = form.cleaned_data["biography"]
                update.website = form.cleaned_data["website"]
                update.linkedin = form.cleaned_data["linkedin"]
                update.github = form.cleaned_data["github"]
                update.publications = form.cleaned_data["publications"]
                if form.cleaned_data["discard_photo"]:
                    update.photo_data = b""
                if form.cleaned_data["photo"]:
                    update.photo_data = form.cleaned_data["photo"]
                if action == "submit":
                    update.status = "submitted"
                    update.submitted_at = timezone.now()
                update.save()
                messages.success(request, "Submitted for review. Your public profile has not changed." if action == "submit" else "Draft saved. Your public profile has not changed.")
                return redirect("staff_portal:profile")
    return render(request, "staff/portal/profile.html", {
        "form": form, "member": access.member, "update": update,
        "submitted": submitted, "history": access.updates.select_related("reviewed_by")[:10],
    })


@staff_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("staff_portal:profile")
    return render(request, "staff/portal/form.html", {"form": form, "title": "Change password", "button_label": "Change password"})


@staff_required
@require_http_methods(["GET", "POST"])
def training_report(request, assignment_id):
    assignment = get_object_or_404(
        StaffTrainingAssignment.objects.select_related("member"),
        pk=assignment_id,
        member=request.staff_access.member,
    )
    if assignment.status == StaffTrainingAssignment.Status.CANCELLED:
        raise PermissionDenied("A report cannot be submitted for a cancelled assignment.")
    report = StaffTrainingReport.objects.filter(assignment=assignment).first()
    locked = bool(report and report.status in [StaffTrainingReport.Status.SUBMITTED, StaffTrainingReport.Status.APPROVED])
    form = StaffTrainingReportForm(request.POST or None, request.FILES or None, instance=report)
    if request.method == "POST":
        action = request.POST.get("action")
        if locked:
            messages.error(request, "This report is locked while it is awaiting review or after approval.")
            return redirect("staff_portal:training_report", assignment_id=assignment.pk)
        if action not in {"save", "submit"}:
            return HttpResponse("Unknown action", status=400)
        if form.is_valid():
            with transaction.atomic():
                report = form.save(commit=False)
                report.assignment = assignment
                report.status = StaffTrainingReport.Status.SUBMITTED if action == "submit" else StaffTrainingReport.Status.DRAFT
                report.submitted_at = timezone.now() if action == "submit" else None
                report.reviewer_comment = "" if action == "submit" else report.reviewer_comment
                report.save()
                form.save_documents(report)
                if action == "submit":
                    queue_report_submitted_notifications(report)
            messages.success(request, "Report submitted to HR for approval." if action == "submit" else "Report draft saved.")
            return redirect("staff_portal:training_report", assignment_id=assignment.pk)
    return render(request, "staff/portal/training_report.html", {
        "assignment": assignment,
        "report": report,
        "form": form,
        "locked": locked,
        "drive_url": getattr(settings, "STAFF_GOOGLE_DRIVE_URL", ""),
    })


@never_cache
def training_report_download(request, document_id):
    document = get_object_or_404(
        StaffTrainingReportDocument.objects.select_related("report__assignment__member"),
        pk=document_id,
    )
    report = document.report
    owns_report = (
        request.user.is_authenticated
        and hasattr(request.user, "staff_profile_access")
        and request.user.staff_profile_access.member_id == report.assignment.member_id
        and report.assignment.member.is_current_staff
    )
    if not owns_report and not (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.has_perm("staff.review_staff_profiles")
    ):
        raise PermissionDenied
    try:
        response = FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.original_name,
            content_type="application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
    except FileNotFoundError as exc:
        raise Http404 from exc


@never_cache
def photo_preview(request, update_id):
    update = get_object_or_404(StaffProfileUpdate.objects.select_related("access"), pk=update_id)
    if not request.user.is_authenticated or not request.user.is_active or not (
        (update.access.user_id == request.user.pk and update.access.member.is_current_staff) or request.user.has_perm("staff.review_staff_profiles")
    ):
        raise PermissionDenied
    if not update.photo_data:
        return HttpResponse(status=404)
    response = HttpResponse(bytes(update.photo_data), content_type="image/jpeg")
    response["X-Content-Type-Options"] = "nosniff"
    return response


@reviewer_required
@require_http_methods(["GET", "POST"])
def dashboard(request):
    form = StaffInvitationForm(request.POST or None, initial={"member": request.GET.get("member")})
    if request.method == "POST":
        # Creating accounts is deliberately reserved for superusers in this pilot.
        if not request.user.is_superuser:
            raise PermissionDenied
        if form.is_valid():
            try:
                invite_staff(form.cleaned_data["member"], form.cleaned_data["email"], request)
            except ValidationError as exc:
                form.add_error(None, exc)
            except IntegrityError:
                form.add_error(None, "An account or invitation already exists. Reload and check the account list.")
            except Exception:
                # Never expose an invitation token or SMTP credentials in the UI.
                logger.warning("Staff invitation delivery failed; administrator should check SMTP configuration.")
                form.add_error(None, "The invitation could not be sent. Check SMTP configuration, then resend using the same staff member and email.")
            else:
                messages.success(request, "Invitation sent. The staff member will choose their own password.")
                return redirect("staff_profile_dashboard")
    members = StaffMember.objects.select_related("department", "profile_access__user", "profile_access__linked_by", "employment").order_by("name", "pk")
    bulk_invite_candidates = list(profile_update_invitation_candidates()) if request.user.is_superuser else []
    return render(request, "staff/admin/dashboard.html", {
        "form": form,
        "staff_members": members,
        "console_email": settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend",
        "submissions": StaffProfileUpdate.objects.filter(status="submitted").select_related("access__member"),
        "recent": StaffProfileUpdate.objects.filter(status__in=["approved", "changes_requested", "withdrawn"]).select_related("access__member", "reviewed_by")[:20],
        "training_assignments": StaffTrainingAssignment.objects.select_related("member", "report", "assigned_by")[:30],
        "submitted_reports": StaffTrainingReport.objects.filter(status=StaffTrainingReport.Status.SUBMITTED).select_related("assignment__member"),
        "bulk_invite_candidates": bulk_invite_candidates,
        "unlinked_current_staff_count": members.filter(profile_access__isnull=True).exclude(
            employment__status__in=["retired", "left"]
        ).count(),
    })


def profile_update_invitation_candidates():
    """Active staff accounts without a submitted or approved profile update."""
    return (
        StaffProfileAccess.objects.select_related("member", "user")
        .filter(user__is_active=True)
        .exclude(user__email="")
        .exclude(member__employment__status__in=["retired", "left"])
        .exclude(updates__status__in=[StaffProfileUpdate.Status.SUBMITTED, StaffProfileUpdate.Status.APPROVED])
        .order_by("member__name", "pk")
        .distinct()
    )


@reviewer_required
@require_POST
def bulk_invite_profile_updates(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.POST.get("confirm") != "yes":
        messages.error(request, "Confirm that you want to email all eligible staff members.")
        return redirect("staff_profile_dashboard")

    invitation_count = 0
    reminder_count = 0
    failure_count = 0
    for access in profile_update_invitation_candidates():
        try:
            if not access.accepted_at and not access.linked_at and not access.user.has_usable_password():
                invite_staff(access.member, access.user.email, request)
                invitation_count += 1
            else:
                send_profile_update_reminder(access, request)
                reminder_count += 1
        except Exception:
            failure_count += 1
            logger.warning("Bulk staff profile invitation failed for access id %s", access.pk, exc_info=True)

    sent_count = invitation_count + reminder_count
    if sent_count:
        messages.success(
            request,
            f"Sent {invitation_count} invitation(s) and {reminder_count} profile reminder(s).",
        )
    else:
        messages.info(request, "No eligible staff profile invitations or reminders were sent.")
    if failure_count:
        messages.warning(request, f"{failure_count} message(s) could not be sent. Check the email configuration and try again.")
    return redirect("staff_profile_dashboard")


@reviewer_required
@require_http_methods(["GET", "POST"])
def assign_training(request):
    form = StaffTrainingAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            assignments = form.save(request.user)
            queue_training_assigned_notifications(assignments)
        messages.success(request, f"{len(assignments)} staff member(s) were assigned to {assignments[0].title}.")
        return redirect("staff_profile_dashboard")
    return render(request, "staff/admin/assign_training.html", {"form": form})


@reviewer_required
@require_http_methods(["GET", "POST"])
def review_training_report(request, report_id):
    report = get_object_or_404(StaffTrainingReport.objects.select_related("assignment__member"), pk=report_id)
    form = StaffTrainingReportReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            report, message = review_training_report_submission(
                report.pk,
                request.user,
                form.cleaned_data["action"],
                form.cleaned_data["comment"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, message)
            return redirect("staff_profile_dashboard")
    return render(request, "staff/admin/review_training_report.html", {"report": report, "form": form})


@reviewer_required
@require_http_methods(["GET", "POST"])
def link_user(request, member_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    member = get_object_or_404(StaffMember.objects.select_related("profile_access__user", "profile_access__linked_by"), pk=member_id)
    access = getattr(member, "profile_access", None)
    form = StaffLinkUserForm(request.POST if request.method == "POST" else None)
    eligible = member.is_current_staff and not access
    if request.method == "POST":
        if not eligible:
            form.add_error(None, "This profile is already linked or is no longer current. Existing account links cannot be replaced here.")
        elif form.is_valid():
            try:
                link_existing_staff_user(member.pk, form.cleaned_data["user"].pk, request.user)
            except ValidationError as exc:
                form.add_error(None, exc)
            except IntegrityError:
                form.add_error(None, "An account link was created by another request. Reload and check the staff list.")
            else:
                messages.success(request, "Existing account linked. Its password, permissions and platform access are unchanged. No password-setup invitation was sent.")
                return redirect("staff_profile_dashboard")
    return render(request, "staff/admin/link_user.html", {"member": member, "account": access, "form": form, "eligible": eligible})


@reviewer_required
@require_http_methods(["GET", "POST"])
def edit_member(request, member_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    member = get_object_or_404(StaffMember.objects.select_related("profile_access__user"), pk=member_id)
    initial = profile_initial(member, None)
    initial.update(name=member.name, role=member.role, department=member.department_id, source_fingerprint=member_fingerprint(member))
    form = StaffEditForm(request.POST if request.method == "POST" else None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            edit_staff_member(member.pk, form.cleaned_data, request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Staff details updated. Page selections and the registered email have not changed.")
            return redirect("staff_profile_dashboard")
    return render(request, "staff/admin/edit.html", {"form": form, "member": member})


@reviewer_required
@require_http_methods(["GET", "POST"])
def employment_change(request, member_id, action):
    if not request.user.is_superuser:
        raise PermissionDenied
    member = get_object_or_404(StaffMember.objects.select_related("employment", "profile_access__user"), pk=member_id)
    offboarding = action == "offboard"
    form = (StaffOffboardingForm if offboarding else StaffReactivationForm)(request.POST if request.method == "POST" else None)
    access = getattr(member, "profile_access", None)
    if offboarding and not access:
        form.fields["disable_account"].disabled = True
        form.fields["disable_account"].help_text = "This member has no linked platform account."
    if request.method == "POST" and form.is_valid():
        try:
            change_staff_employment(
                member.pk, request.user, form.cleaned_data["status"] if offboarding else "active",
                form.cleaned_data["effective_date"] if offboarding else timezone.localdate(),
                form.cleaned_data.get("disable_account", False),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Staff member offboarded. Their profile and history have been retained." if offboarding else "Staff profile reactivated. Disabled accounts must be enabled separately in Settings → Users; pending invitations must be resent.")
            return redirect("staff_profile_dashboard")
    return render(request, "staff/admin/employment.html", {
        "member": member, "form": form, "offboarding": offboarding, "account": access,
        "events": StaffEmploymentEvent.objects.filter(employment__member=member).select_related("actor"),
    })


@reviewer_required
@require_http_methods(["GET", "POST"])
def create_member(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = StaffCreateForm(request.POST if request.method == "POST" else None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            member = create_staff_member(form.cleaned_data, request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{member.name} was added and published on the Our Team page.")
            if form.cleaned_data["send_invitation"]:
                try:
                    invite_staff(member, form.cleaned_data["email"], request)
                except ValidationError as exc:
                    messages.error(request, "The staff record was saved, but no invitation was sent: " + " ".join(exc.messages))
                except Exception:
                    logger.warning("Invitation delivery failed after staff creation; administrator should check SMTP configuration.")
                    messages.error(request, "The staff record was saved, but the invitation could not be sent. Check email settings and resend from the invitation form below. Do not add the staff member again.")
                else:
                    messages.success(request, "Invitation sent. The staff member will choose their own password.")
            return redirect(reverse("staff_profile_dashboard") + f"?member={member.pk}")
    return render(request, "staff/admin/create.html", {
        "form": form,
        "console_email": settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend",
        "has_team_page": form.fields["team_page"].queryset.exists(),
    })


@reviewer_required
@require_http_methods(["GET", "POST"])
def review(request, update_id):
    update = get_object_or_404(StaffProfileUpdate.objects.select_related("access__member"), pk=update_id)
    form = StaffReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            review_update(update.pk, request.user, form.cleaned_data["action"], form.cleaned_data["comment"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Profile approved and published." if form.cleaned_data["action"] == "approve" else "Changes requested. The public profile is unchanged.")
            return redirect("staff_profile_dashboard")
    return render(request, "staff/admin/review.html", {"update": update, "member": update.access.member, "form": form})
