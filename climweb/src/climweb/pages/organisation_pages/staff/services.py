import hashlib
import json
import secrets
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html_join, strip_tags
from wagtail.images import get_image_model
from wagtailcache.cache import clear_cache
from PIL import Image

from .models import StaffEmployment, StaffEmploymentEvent, StaffMember, StaffPage, StaffPageSelection, StaffProfileAccess, StaffProfileUpdate


INVITATION_LIFETIME = timedelta(hours=48)


@transaction.atomic
def link_existing_staff_user(member_id, user_id, administrator):
    if not administrator.is_active or not administrator.is_superuser:
        raise ValidationError("Only a superuser can link existing accounts.")
    member = StaffMember.objects.select_for_update().get(pk=member_id)
    if not member.is_current_staff:
        raise ValidationError("Reactivate this staff profile before linking an account.")
    User = get_user_model()
    user = User.objects.select_for_update().get(pk=user_id)
    if not user.is_active:
        raise ValidationError("This account is disabled. Review its access in Settings → Users first.")
    if not user.email:
        raise ValidationError("This account needs a registered email address before it can be linked.")
    validate_email(user.email)
    if User.objects.filter(email__iexact=user.email).exclude(pk=user.pk).exists():
        raise ValidationError("More than one account uses this email. Resolve the duplicate addresses in Settings → Users first.")
    if StaffProfileAccess.objects.filter(member=member).exists():
        raise ValidationError("This staff profile is already linked to an account. Existing links cannot be replaced here.")
    if StaffProfileAccess.objects.filter(user=user).exists():
        raise ValidationError("This account is already linked to another staff profile.")
    now = timezone.now()
    # Do not modify the User, password, flags, groups or permissions. Existing
    # platform access remains governed by the platform's normal authorization.
    return StaffProfileAccess.objects.create(
        member=member, user=user, profile_only=False, accepted_at=now,
        linked_at=now, linked_by=administrator,
    )


@transaction.atomic
def change_staff_employment(member_id, administrator, status, effective_date, disable_account=False):
    if not administrator.is_active or not administrator.is_superuser:
        raise ValidationError("Only a superuser can offboard or reactivate staff.")
    if status not in StaffEmployment.Status.values or effective_date > timezone.localdate():
        raise ValidationError("Choose a valid status and an effective date no later than today.")
    member = StaffMember.objects.select_for_update().get(pk=member_id)
    employment = StaffEmployment.objects.filter(member=member).first()
    previous_status = employment.status if employment else StaffEmployment.Status.ACTIVE
    if previous_status == status or (previous_status != "active" and status != "active"):
        raise ValidationError("This staff member's status has changed. Reload the page before continuing.")
    access = StaffProfileAccess.objects.select_for_update().filter(member=member).first()
    if disable_account and (status == "active" or not access or access.user_id == administrator.pk):
        raise ValidationError("You cannot disable this account through this action.")
    if not employment:
        employment = StaffEmployment(member=member)
    employment.status = status
    employment.effective_date = effective_date
    employment.save()
    if access and status != "active":
        access.invitation_digest = ""
        access.save(update_fields=["invitation_digest"])
        access.updates.filter(status__in=["draft", "submitted"]).update(
            status=StaffProfileUpdate.Status.WITHDRAWN, reviewed_by=administrator,
            reviewed_at=timezone.now(), reviewer_comment="Withdrawn because the staff member was offboarded.",
        )
        if disable_account:
            User = get_user_model()
            User.objects.filter(pk=access.user_id).update(is_active=False)
    StaffEmploymentEvent.objects.create(
        employment=employment, previous_status=previous_status, status=status,
        effective_date=effective_date, actor=administrator, account_disabled=disable_account,
    )
    # Public team and homepage DG identity are cached independently of revisions.
    transaction.on_commit(clear_cache)
    transaction.on_commit(cache.clear)
    return employment


def biography_html(text):
    return str(format_html_join("", "<p>{}</p>", ((part.strip(),) for part in text.split("\n\n") if part.strip())))


def save_staff_portrait(name, photo_data):
    with Image.open(BytesIO(bytes(photo_data))) as portrait:
        width, height = portrait.size
    image = get_image_model()(title=f"{name} — staff profile", width=width, height=height)
    image.file.save(f"staff-{secrets.token_hex(12)}.jpg", ContentFile(bytes(photo_data)), save=False)
    image.width, image.height = width, height
    image.save()
    return image


@transaction.atomic
def create_staff_member(data, administrator):
    """Publish a new inline record without publishing unrelated page drafts."""
    if not administrator.is_active or not administrator.is_superuser:
        raise ValidationError("Only an administrator can add a staff member here.")
    page = StaffPage.objects.select_for_update().get(pk=data["team_page"].pk)
    if not page.permissions_for_user(administrator).can_publish():
        raise ValidationError("You need permission to publish the Our Team page.")
    if not page.live or page.has_unpublished_changes or page.locked:
        raise ValidationError("The Our Team page is unpublished, locked, or has an unpublished draft. Resolve that draft or lock in Pages before adding a staff member here.")
    if page.staffmembers.filter(name__iexact=data["name"], role__iexact=data["role"], department=data["department"]).exists():
        raise ValidationError("A staff member with this name, job title and department already exists. Use the existing member in the invitation form instead.")
    members = list(page.staffmembers.all())
    member = StaffMember(
        page=page, name=data["name"], role=data["role"], department=data["department"],
        bio=biography_html(data["biography"]), website=data["website"], linkedin=data["linkedin"],
        github=data["github"], publications=data["publications"],
        sort_order=max((item.sort_order or 0 for item in members), default=-1) + 1,
    )
    if data.get("photo"):
        member.photo = save_staff_portrait(member.name, data["photo"])
    # Give the inline a stable ID before revision serialization. This insertion
    # and the page publication are in one transaction and roll back together.
    member.full_clean()
    member.save()
    page.staffmembers.set([*members, member])
    selections = list(page.selected_staff.all())
    page.selected_staff.add(StaffPageSelection(member=member, sort_order=max((entry.sort_order or 0 for entry in selections), default=-1) + 1))
    page.save_revision(user=administrator).publish(user=administrator)
    return member


@transaction.atomic
def edit_staff_member(member_id, data, administrator):
    if not administrator.is_active or not administrator.is_superuser:
        raise ValidationError("Only a superuser can edit official staff details.")
    member = StaffMember.objects.select_for_update().get(pk=member_id)
    if member_fingerprint(member) != data["source_fingerprint"]:
        raise ValidationError("This profile changed while you were editing. Reload the form before saving.")
    page = StaffPage.objects.select_for_update().get(pk=member.page_id)
    if not page.permissions_for_user(administrator).can_publish() or not page.live or page.has_unpublished_changes or page.locked:
        raise ValidationError("Resolve unpublished drafts or locks on the Our Team page before editing staff details.")
    members = list(page.staffmembers.all())
    member = next(item for item in members if item.pk == member_id)
    for field in ["name", "role", "department", "website", "linkedin", "github", "publications"]:
        setattr(member, field, data[field])
    original_text = strip_tags((member.bio or "").replace("</p>", "\n\n")).strip()
    if data["biography"] != original_text:
        member.bio = biography_html(data["biography"])
    if data.get("photo"):
        member.photo = save_staff_portrait(member.name, data["photo"])
    member.full_clean()
    page.staffmembers.set(members)
    page.save_revision(user=administrator).publish(user=administrator)
    transaction.on_commit(clear_cache)
    transaction.on_commit(cache.clear)
    return member


def member_fingerprint(member):
    values = [member.name, member.role, member.department_id, member.bio, member.photo_id, member.website, member.linkedin]
    # Keep pre-upgrade pending submissions valid when all new fields are empty.
    contact_fields = [member.github, member.publications, member.public_email]
    if any(contact_fields):
        values.extend(contact_fields)
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def invitation_valid(access, token):
    return bool(
        access.user.is_active and access.member.is_current_staff and access.invitation_digest and access.invited_at
        and timezone.now() < access.invited_at + INVITATION_LIFETIME
        and secrets.compare_digest(access.invitation_digest, hashlib.sha256(token.encode()).hexdigest())
    )


def invite_staff(member, email, request):
    email = email.strip().lower()
    User = get_user_model()
    with transaction.atomic():
        # Serialize invitations for the same existing staff record.
        member = StaffMember.objects.select_for_update().get(pk=member.pk)
        if not member.is_current_staff:
            raise ValidationError("Former staff cannot be invited. Reactivate the staff profile first.")
        access = StaffProfileAccess.objects.filter(member=member).select_related("user").first()
        if access:
            if access.accepted_at or not access.user.is_active:
                raise ValidationError("This account is already activated or disabled. Active staff can use the password reset page.")
            if access.user.email.lower() != email:
                raise ValidationError("This profile is already linked to another email address.")
        else:
            if User.objects.filter(email__iexact=email).exists() or User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": email}).exists():
                raise ValidationError("An account already uses this email. Use Link existing user for this staff member instead of sending a new invitation.")
            user = User(**{User.USERNAME_FIELD: email})
            user.email = email
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            user.full_clean(exclude=["password"])
            user.save()
            access = StaffProfileAccess.objects.create(member=member, user=user)
        token = secrets.token_urlsafe(32)
        access.invitation_digest = hashlib.sha256(token.encode()).hexdigest()
        access.invited_at = timezone.now()
        access.save(update_fields=["invitation_digest", "invited_at"])

    url = request.build_absolute_uri(reverse("staff_portal:accept", args=[access.pk, token]))
    # Intentionally outside the transaction: failed delivery leaves a safe,
    # passwordless account that the administrator can resend an invitation to.
    send_mail(
        "Set up your ACMAD staff profile account",
        f"Hello {member.name},\n\nYou have been invited to manage your ACMAD staff profile.\n"
        f"Set your own password using this single-use link (valid for 48 hours):\n{url}\n\n"
        "Your photo and biography changes will be reviewed before publication.\n"
        "If you were not expecting this invitation, contact your website administrator.\n",
        settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False,
    )
    return access


@transaction.atomic
def review_update(update_id, reviewer, action, comment):
    if not reviewer.is_active or not reviewer.has_perm("staff.review_staff_profiles"):
        raise ValidationError("You do not have permission to review staff profiles.")
    member_id = StaffProfileUpdate.objects.values_list("access__member_id", flat=True).get(pk=update_id)
    member = StaffMember.objects.select_for_update().get(pk=member_id)
    if not member.is_current_staff:
        raise ValidationError("Former staff submissions cannot be reviewed or published.")
    update = StaffProfileUpdate.objects.select_for_update().select_related("access__member", "access__user").get(pk=update_id)
    if update.status != StaffProfileUpdate.Status.SUBMITTED:
        raise ValidationError("This submission has already been reviewed or is not ready for review.")
    if action not in {"approve", "request_changes"}:
        raise ValidationError("Unknown review action.")
    if action == "approve":
        if not update.access.user.is_active:
            raise ValidationError("This staff account is disabled.")
        page = StaffPage.objects.select_for_update().get(pk=update.access.member.page_id)
        if not page.permissions_for_user(reviewer).can_publish():
            raise ValidationError("You also need Wagtail publish permission for the Our Team page to approve this profile.")
        if not page.live or page.has_unpublished_changes or page.locked:
            raise ValidationError("The Our Team page is unpublished, locked, or has an unpublished draft. Resolve that draft or lock in Pages before approving this profile.")
        # Update through the page's revision system, never bypass a pending page
        # draft or silently replace a concurrent administrator's profile edits.
        members = list(page.staffmembers.all())
        member = next((item for item in members if item.pk == update.access.member_id), None)
        if member is None or member_fingerprint(member) != update.source_fingerprint:
            raise ValidationError("The public profile changed after this draft was created. Request changes so the staff member can prepare a fresh submission.")
        member.bio = biography_html(update.biography)
        member.website = update.website
        member.linkedin = update.linkedin
        member.github = update.github
        member.publications = update.publications
        if update.photo_data:
            member.photo = save_staff_portrait(member.name, update.photo_data)
        page.staffmembers.set(members)
        page.save_revision(user=reviewer).publish(user=reviewer)
        update.status = StaffProfileUpdate.Status.APPROVED
    else:
        if not comment.strip():
            raise ValidationError("Please explain the requested changes.")
        update.status = StaffProfileUpdate.Status.CHANGES_REQUESTED
    update.reviewer_comment = comment
    update.reviewed_by = reviewer
    update.reviewed_at = timezone.now()
    update.save()
    return update
