import json
import os

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from wagtail.admin import messages

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.mail import get_connection
from django.db.models import Avg
from django.http import Http404
from django.shortcuts import get_object_or_404
from wagtail.contrib.forms.models import FormMixin
from wagtail.contrib.forms.utils import get_forms_for_user
from wagtail.models import Page

from climweb import __version__
from climweb.base.mail import send_mail
from climweb.base.utils import get_latest_cms_release, send_upgrade_command, send_plugin_remove, get_installed_plugins, \
    mix_with_white
from climweb.utils.version import check_version_greater_than_current, get_main_version
from .forms import CMSUpgradeForm
from .models import Theme, OrganisationSetting, FormFileSubmission, SubmissionReview, SubmissionEmailLog


def handler500(request):
    context = {}
    response = render(request, "500.html", context=context)
    response.status_code = 500
    return response


def humans(request):
    return render(request, "humans.txt", context={}, content_type="text/plain; charset=utf-8", )


def cms_version_view(request):
    # set upgrade status
    if cache.get("cms_upgrade_pending") is None:
        cache.set("cms_upgrade_pending", False)
    
    cms_upgrade_pending = cache.get("cms_upgrade_pending")
    
    template_name = "admin/cms_version.html"
    cms_upgrade_hook_url = getattr(settings, "CMS_UPGRADE_HOOK_URL", None)
    
    try:
        latest_release = get_latest_cms_release()
        latest_version = latest_release.get("version")
    except Exception as e:
        return render(request, template_name,
                      context={
                          "error": True,
                          "error_message": _("Error fetching latest version. Please try again later."),
                          "error_traceback": str(e)
                      })
    
    current_version = get_main_version()
    
    context = {
        "latest_release": latest_release,
        "current_version": current_version,
        "cms_upgrade_hook_url": cms_upgrade_hook_url,
    }
    
    try:
        latest_release_greater_than_current = check_version_greater_than_current(latest_version)
    except Exception as e:
        return render(request, template_name,
                      context={
                          "error": True,
                          "error_message": _("Error in extracting latest version number from the release"),
                          "error_traceback": str(e)
                      })
    
    context.update({
        "has_new_version": latest_release_greater_than_current,
    })
    
    initial = {
        "latest_version": latest_version,
        "current_version": current_version
    }
    
    form = CMSUpgradeForm(initial=initial)
    
    context.update({
        "form": form,
    })
    
    upgrade_form = CMSUpgradeForm(initial=initial)
    
    if request.POST:
        form = CMSUpgradeForm(request.POST)
        
        if form.is_valid():
            current_version = form.cleaned_data.get("current_version")
            latest_version = form.cleaned_data.get("latest_version")
            
            if cms_upgrade_hook_url:
                if cms_upgrade_pending:
                    messages.warning(request, "ClimWeb upgrade already initiated")
                else:
                    try:
                        send_upgrade_command(latest_version)
                        cache.set("cms_upgrade_pending", True)
                        messages.success(request, "ClimWeb upgrade initiated successfully")
                        return redirect("wagtailadmin_home")
                    except Exception as e:
                        cache.set("cms_upgrade_pending", False)
                        messages.error(request, "Error initiating ClimWeb upgrade. Please ensure the "
                                                "'CMS_UPGRADE_HOOK_URL' env variable is working correctly")
                        context.update({
                            "form": upgrade_form
                        })
    else:
        context.update({
            "form": upgrade_form
        })
    
    context.update({"cms_upgrade_pending": cache.get("cms_upgrade_pending")})
    
    return render(request, template_name, context=context)


def plugin_manager_view(request):
    if not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    
    template_name = "admin/plugin_manager.html"
    plugin_manage_hook_url = getattr(settings, "CMS_PLUGIN_MANAGE_HOOK_URL", None)
    plugins = get_installed_plugins()
    
    if request.method == "POST":
        plugin_name = request.POST.get("plugin_name", "").strip()
        if not plugin_name:
            messages.error(request, _("No plugin name provided."))
        elif not plugin_manage_hook_url:
            messages.error(request, _("CMS_PLUGIN_MANAGE_HOOK_URL is not configured."))
        else:
            try:
                send_plugin_remove(plugin_name)
                messages.success(
                    request,
                    _("Plugin '%(name)s' removal initiated. The server will restart shortly.") % {"name": plugin_name},
                )
                return redirect("plugin-manager")
            except Exception:
                messages.error(request,
                               _("Error sending remove command. Check that CMS_PLUGIN_MANAGE_HOOK_URL is reachable."))
    
    return render(request, template_name, context={
        "plugins": plugins,
        "plugin_manage_hook_url": plugin_manage_hook_url,
    })


_DEFAULT_TOKENS = {
    "primary": "#0C447C",
    "primary-light": mix_with_white("#0C447C", 0.75),
    "primary-medium": mix_with_white("#0C447C", 0.50),
    "background": mix_with_white("#0C447C", 0.80),
    "text": "#363636",
    "border-radius": "0.72em",
    "box-shadow-elevation": "6",
}


def _build_tokens():
    try:
        theme = Theme.objects.get(is_default=True)
        primary = theme.primary_hover_color
        return {
            "primary": primary,
            "primary-light": mix_with_white(primary, 0.75),
            "primary-medium": mix_with_white(primary, 0.50),
            "background": mix_with_white(primary, 0.80),
            "text": theme.primary_color,
            "border-radius": f"{theme.border_radius * 0.06}em",
            "box-shadow-elevation": str(theme.box_shadow),
        }
    except ObjectDoesNotExist:
        return _DEFAULT_TOKENS


def style_guide(request):
    try:
        org_setting = OrganisationSetting.for_request(request)
    except Exception:
        org_setting = None
    tokens = _build_tokens()
    context = {
        "tokens": tokens,
        # Flattened aliases so the template avoids hyphenated key access
        "token_primary": tokens["primary"],
        "token_primary_light": tokens["primary-light"],
        "token_primary_medium": tokens["primary-medium"],
        "token_background": tokens["background"],
        "token_text": tokens["text"],
        "token_border_radius": tokens["border-radius"],
        "token_box_shadow": tokens["box-shadow-elevation"],
        "org_setting": org_setting,
    }
    return render(request, "base/style_guide.html", context)


def style_guide_tokens(request):
    return JsonResponse(_build_tokens())


def public_health_check(request):
    return JsonResponse({
        "version": __version__,
    })


def cms_upgrade_status_view(request):
    """
    JSON endpoint polled by the frontend to show live upgrade progress.
    Reads upgrade-status.json written by cms-upgrade.sh into the backup volume.
    """
    backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get("location", "")
    status_file = os.path.join(backup_dir, "upgrade-status.json")
    
    status_data = {}
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                status_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            status_data = {"status": "unknown", "step": "Could not read status file."}
    
    # If the upgrade finished (success or failed), clear the pending flag from cache
    terminal = status_data.get("status") in ("success", "failed")
    if terminal:
        cache.set("cms_upgrade_pending", False)
    
    status_data["cms_upgrade_pending"] = cache.get("cms_upgrade_pending", False)

    return JsonResponse(status_data)


def _get_submission_field_rows(page, submission):
    """Build a label/value row per submitted field, resolving image/document
    fields to their actual FormFileSubmission so the review page can render
    them inline (img/iframe) instead of linking out to a download.

    Mirrors the field_type lookup CustomSubmissionsListView already uses
    (climweb/base/forms.py) so both views agree on which fields are files.
    """
    fields_by_type = {field.clean_name: field.field_type for field in page.get_form_fields()}
    form_data = submission.get_data()
    rows = []

    for name, label in page.get_data_fields():
        value = form_data.get(name)
        field_type = fields_by_type.get(name)

        # Checkboxes/multiselect fields store a list - join it for display,
        # matching Wagtail's own SubmissionsListView and this project's
        # existing ContactPage.send_suspicious_form_to_admin convention.
        if isinstance(value, list):
            value = ", ".join(value)

        # has_value tracks "was this field genuinely answered" separately
        # from the value's own truthiness, so a real False/0 answer (e.g.
        # an unchecked checkbox) isn't shown identically to a blank field.
        row = {"label": label, "field_type": field_type, "value": value,
               "has_value": value is not None and value != "", "file_url": None}

        if field_type in ("image", "document") and value:
            try:
                file_submission = FormFileSubmission.objects.get(pk=value)
                row["file_url"] = file_submission.file.url
                row["file_name"] = file_submission.file.name.split("/")[-1]
            except (FormFileSubmission.DoesNotExist, ValueError, TypeError):
                row["value"] = None
                row["has_value"] = False

        rows.append(row)

    return rows


def submission_review_view(request, page_id, submission_id):
    """Detail + review view for a single form submission, for any Wagtail
    form page sitewide (events, data requests, summer school applications,
    ...) - submission models are generated per page type, so the page and
    submission are resolved generically here rather than via one shared
    submissions table.

    Uses the same page-level "change" permission Wagtail's own
    SubmissionsListView requires to view the submissions list at all, so
    any staff member who can already see the list can also review entries
    in it - not gated to superusers.
    """
    if not get_forms_for_user(request.user).filter(pk=page_id).exists():
        raise PermissionDenied

    page = get_object_or_404(Page, id=page_id).specific
    if not isinstance(page, FormMixin):
        raise Http404

    submission = get_object_or_404(page.get_submission_class(), pk=submission_id, page=page)
    content_type = ContentType.objects.get_for_model(submission)
    ratings_enabled = getattr(page, "enable_submission_ratings", False)

    if request.method == "POST":
        if not ratings_enabled:
            raise PermissionDenied

        rating = request.POST.get("rating") or None
        comment = request.POST.get("comment", "").strip()

        if rating or comment:
            SubmissionReview.objects.create(
                content_type=content_type,
                object_id=submission.pk,
                reviewer=request.user,
                rating=int(rating) if rating else None,
                comment=comment,
            )
            messages.success(request, _("Review added."))
        else:
            messages.error(request, _("Add a rating or a comment before submitting."))

        return redirect("form_submission_review", page_id=page.id, submission_id=submission.id)

    reviews = SubmissionReview.objects.none()
    avg_rating = None
    if ratings_enabled:
        reviews = SubmissionReview.objects.filter(
            content_type=content_type, object_id=submission.pk,
        ).select_related("reviewer")
        avg_rating = reviews.exclude(rating=None).aggregate(Avg("rating"))["rating__avg"]

    return render(request, "wagtailadmin/submission_review.html", {
        "page": page,
        "submission": submission,
        "ratings_enabled": ratings_enabled,
        "fields": _get_submission_field_rows(page, submission),
        "reviews": reviews,
        "avg_rating": avg_rating,
        "star_range": range(1, 6),
    })


def submissions_ratings_view(request, page_id):
    """Lists a form page's submissions sorted by average rating (highest
    first), with checkboxes to select a batch and send them an email (see
    compose_submission_email_view below). Only meaningful when the page has
    ratings enabled at all.
    """
    if not get_forms_for_user(request.user).filter(pk=page_id).exists():
        raise PermissionDenied

    page = get_object_or_404(Page, id=page_id).specific
    if not isinstance(page, FormMixin):
        raise Http404

    if not getattr(page, "enable_submission_ratings", False):
        messages.error(request, _("Ratings are not enabled for this form."))
        return redirect("wagtailforms:list_submissions", page_id=page.id)

    submissions = list(page.get_submissions())
    content_type = ContentType.objects.get_for_model(page.get_submission_class())

    reviews_by_submission = {}
    for review in SubmissionReview.objects.filter(
        content_type=content_type, object_id__in=[s.pk for s in submissions]
    ):
        reviews_by_submission.setdefault(review.object_id, []).append(review)

    # Heuristic used across every form on this site so far: the applicant's
    # display name lives in a field whose clean_name is literally "name".
    name_field = next((n for n, label in page.get_data_fields() if n == "name"), None)

    rows = []
    for submission in submissions:
        data = submission.get_data()
        reviews = reviews_by_submission.get(submission.pk, [])
        ratings = [r.rating for r in reviews if r.rating]
        avg = sum(ratings) / len(ratings) if ratings else None
        rows.append({
            "submission": submission,
            "name": data.get(name_field) if name_field else None,
            "avg_rating": avg,
            "avg_rating_rounded": round(avg) if avg else 0,
            "review_count": len(reviews),
        })

    rows.sort(key=lambda r: (r["avg_rating"] is None, -(r["avg_rating"] or 0)))

    return render(request, "wagtailadmin/submissions_ratings.html", {
        "page": page,
        "rows": rows,
        "star_range": range(1, 6),
    })


def compose_submission_email_view(request, page_id):
    """Two-step POST flow reached from submissions_ratings_view's selection
    form: first POST (no "subject" key yet) just renders the compose form
    for the selected submissions; the compose form's own POST (has
    "subject") actually mail-merges {{ name }} per recipient, sends, and
    logs the batch to SubmissionEmailLog.
    """
    if not get_forms_for_user(request.user).filter(pk=page_id).exists():
        raise PermissionDenied

    page = get_object_or_404(Page, id=page_id).specific
    if not isinstance(page, FormMixin):
        raise Http404

    if request.method != "POST":
        raise Http404

    submission_ids = request.POST.getlist("submission_ids")
    if not submission_ids:
        messages.error(request, _("No submissions selected."))
        return redirect("submissions_ratings", page_id=page.id)

    submission_class = page.get_submission_class()
    submissions = list(submission_class.objects.filter(pk__in=submission_ids, page=page))
    content_type = ContentType.objects.get_for_model(submission_class)

    fields_by_type = {f.clean_name: f.field_type for f in page.get_form_fields()}
    email_field = next((n for n, t in fields_by_type.items() if t == "email"), None)
    name_field = "name" if "name" in fields_by_type else None

    if "subject" in request.POST:
        subject = request.POST.get("subject", "").strip()
        body = request.POST.get("body", "")
        attachments = request.FILES.getlist("attachments")

        if not subject or not body:
            messages.error(request, _("Subject and message body are required."))
        else:
            sent_to = []
            skipped = 0
            # One shared SMTP connection for the whole batch instead of a
            # fresh connection per recipient (send_mail's connection= kwarg
            # exists precisely for this).
            connection = get_connection()
            connection.open()
            try:
                for submission in submissions:
                    data = submission.get_data()
                    recipient = data.get(email_field) if email_field else None
                    if not recipient:
                        skipped += 1
                        continue
                    name = (data.get(name_field) or "") if name_field else ""
                    personalized_body = body.replace("{{ name }}", name).replace("{{name}}", name)
                    send_mail(subject, personalized_body, [recipient], attachments=attachments,
                             connection=connection)
                    sent_to.append(recipient)
            finally:
                connection.close()

            if sent_to:
                # Only log a batch as "sent" if at least one email actually
                # went out - otherwise this would leave a misleading audit
                # row claiming a send that never happened.
                SubmissionEmailLog.objects.create(
                    content_type=content_type,
                    submission_ids=[s.pk for s in submissions],
                    recipients=sent_to,
                    subject=subject,
                    body=body,
                    attachment_names=[f.name for f in attachments],
                    sent_by=request.user,
                )
                messages.success(
                    request,
                    _("Email sent to %(count)d recipient(s).") % {"count": len(sent_to)},
                )
            if skipped:
                messages.warning(
                    request,
                    _("%(count)d submission(s) skipped — no email address found.") % {"count": skipped},
                )

            return redirect("submissions_ratings", page_id=page.id)

    recipient_rows = []
    for submission in submissions:
        data = submission.get_data()
        recipient_rows.append({
            "name": (data.get(name_field) if name_field else None) or "—",
            "email": (data.get(email_field) if email_field else None),
        })

    return render(request, "wagtailadmin/compose_submission_email.html", {
        "page": page,
        "submission_ids": submission_ids,
        "recipient_rows": recipient_rows,
        "email_field": email_field,
        "name_field": name_field,
    })
