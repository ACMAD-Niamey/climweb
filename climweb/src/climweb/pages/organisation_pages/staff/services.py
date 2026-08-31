import hashlib
import json
import secrets
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html_join
from wagtail.images import get_image_model
from PIL import Image

from .models import StaffMember, StaffPage, StaffProfileAccess, StaffProfileUpdate


INVITATION_LIFETIME = timedelta(hours=48)


def member_fingerprint(member):
    values = [member.name, member.role, member.department_id, member.bio, member.photo_id, member.website, member.linkedin]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def invitation_valid(access, token):
    return bool(
        access.user.is_active and access.invitation_digest and access.invited_at
        and timezone.now() < access.invited_at + INVITATION_LIFETIME
        and secrets.compare_digest(access.invitation_digest, hashlib.sha256(token.encode()).hexdigest())
    )


def invite_staff(member, email, request):
    email = email.strip().lower()
    User = get_user_model()
    with transaction.atomic():
        # Serialize invitations for the same existing staff record.
        member = StaffMember.objects.select_for_update().get(pk=member.pk)
        access = StaffProfileAccess.objects.filter(member=member).select_related("user").first()
        if access:
            if access.accepted_at or not access.user.is_active:
                raise ValidationError("This account is already activated or disabled. Active staff can use the password reset page.")
            if access.user.email.lower() != email:
                raise ValidationError("This profile is already linked to another email address.")
        else:
            if User.objects.filter(email__iexact=email).exists() or User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": email}).exists():
                raise ValidationError("An account already uses this email. Existing accounts are not automatically linked or given new permissions.")
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
        member.bio = str(format_html_join("", "<p>{}</p>", ((part.strip(),) for part in update.biography.split("\n\n") if part.strip())))
        member.website = update.website
        member.linkedin = update.linkedin
        if update.photo_data:
            with Image.open(BytesIO(bytes(update.photo_data))) as portrait:
                width, height = portrait.size
            image = get_image_model()(title=f"{member.name} — staff profile", width=width, height=height)
            image.file.save(f"staff-{member.pk}-{secrets.token_hex(8)}.jpg", ContentFile(bytes(update.photo_data)), save=False)
            image.width, image.height = width, height
            image.save()
            member.photo = image
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
