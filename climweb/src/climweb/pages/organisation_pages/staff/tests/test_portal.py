import re
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from wagtail.images import get_image_model
from wagtail.models import GroupPagePermission

from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from .factories import StaffPageFactory
from ..forms import StaffProfileForm
from ..models import Department, StaffMember, StaffProfileAccess, StaffProfileUpdate
from ..services import invite_staff, member_fingerprint, review_update


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", AXES_ENABLED=False)
class StaffPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        home = get_or_create_homepage()
        organisation = OrganisationIndexPageFactory(parent=home)
        cls.page = StaffPageFactory(parent=organisation)
        department = Department.objects.create(name="Research")
        cls.member = StaffMember.objects.create(page=cls.page, name="Pilot Staff", role="Scientist", department=department, bio="<p>Original biography.</p>")
        cls.other_member = StaffMember.objects.create(page=cls.page, name="Other Staff", role="Forecaster", department=department)
        cls.page.save_revision().publish()
        User = get_user_model()
        cls.admin = User.objects.create_superuser(username="staff-admin", email="admin@example.test", password="Admin-test-9274!")
        cls.user = User.objects.create_user(username="pilot@example.test", email="pilot@example.test", password="Staff-test-9274!")
        cls.access = StaffProfileAccess.objects.create(member=cls.member, user=cls.user, accepted_at=timezone.now())
        cls.other_user = User.objects.create_user(username="other@example.test", email="other@example.test", password="Other-test-9274!")
        cls.other_access = StaffProfileAccess.objects.create(member=cls.other_member, user=cls.other_user)

    def login_staff(self):
        self.client.force_login(self.user)

    def setUp(self):
        # Isolate throttle counters without touching the application cache.
        cache_settings = override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
        cache_settings.enable()
        self.addCleanup(cache_settings.disable)
        cache.clear()

    def draft(self, status="submitted", **kwargs):
        return StaffProfileUpdate.objects.create(access=self.access, biography="Updated biography.", status=status, source_fingerprint=member_fingerprint(self.member), **kwargs)

    def invite(self):
        # Use an unlinked record rather than repurposing any existing account.
        member = StaffMember.objects.create(page=self.page, name="Invited Staff", role="Scientist", department=self.member.department)
        request = RequestFactory().get("/cms-admin/staff-profiles/", HTTP_HOST="localhost")
        access = invite_staff(member, "invited@example.test", request)
        url = re.search(r"http://localhost(/staff/invite/[^\s]+)", mail.outbox[-1].body).group(1)
        return access, url, request

    def test_invitation_uses_no_default_password_or_cms_permissions(self):
        access, url, _ = self.invite()
        self.assertFalse(access.user.has_usable_password())
        self.assertFalse(access.user.is_staff)
        self.assertFalse(access.user.is_superuser)
        self.assertFalse(access.user.has_perm("wagtailadmin.access_admin"))
        self.assertNotIn(url.split("/")[-2], access.invitation_digest)
        self.assertContains(self.client.get(url), "Set your password")

    def test_accepting_invitation_validates_password_and_prevents_reuse(self):
        access, url, _ = self.invite()
        self.assertEqual(self.client.post(url, {"new_password1": "x", "new_password2": "x"}).status_code, 200)
        access.user.refresh_from_db()
        self.assertFalse(access.user.has_usable_password())
        response = self.client.post(url, {"new_password1": "A-unique-staff-password-9274!", "new_password2": "A-unique-staff-password-9274!"})
        self.assertRedirects(response, reverse("staff_portal:login"))
        access.refresh_from_db()
        access.user.refresh_from_db()
        self.assertTrue(access.user.check_password("A-unique-staff-password-9274!"))
        self.assertTrue(access.accepted_at)
        self.assertEqual(access.invitation_digest, "")
        self.assertEqual(self.client.get(url).status_code, 400)

    def test_expired_resend_and_disabled_invitations(self):
        access, old_url, request = self.invite()
        access.invited_at = timezone.now() - timedelta(hours=49)
        access.save()
        self.assertEqual(self.client.get(old_url).status_code, 400)
        invite_staff(access.member, access.user.email, request)
        new_url = re.search(r"http://localhost(/staff/invite/[^\s]+)", mail.outbox[-1].body).group(1)
        self.assertNotEqual(old_url, new_url)
        self.assertEqual(self.client.get(old_url).status_code, 400)
        self.assertEqual(self.client.get(new_url).status_code, 200)
        access.user.is_active = False
        access.user.save()
        self.assertEqual(self.client.get(new_url).status_code, 400)

    def test_cannot_link_existing_privileged_account(self):
        member = StaffMember.objects.create(page=self.page, name="Another", role="Scientist", department=self.member.department)
        with self.assertRaises(ValidationError):
            invite_staff(member, self.admin.email, RequestFactory().get("/", HTTP_HOST="localhost"))
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())

    def test_email_failure_leaves_resendable_passwordless_account(self):
        with patch("climweb.pages.organisation_pages.staff.services.send_mail", side_effect=OSError("SMTP unavailable")):
            with self.assertRaises(OSError):
                self.invite()
        access = StaffProfileAccess.objects.get(user__email="invited@example.test")
        self.assertFalse(access.user.has_usable_password())

    def test_staff_login_redirects_to_profile_even_with_dashboard_next(self):
        response = self.client.post(reverse("staff_portal:login") + "?next=/cms-admin/", {"username": self.user.username, "password": "Staff-test-9274!"})
        self.assertRedirects(response, reverse("staff_portal:profile"))

    def test_nonstaff_and_disabled_users_cannot_use_portal_login(self):
        response = self.client.post(reverse("staff_portal:login"), {"username": self.admin.username, "password": "Admin-test-9274!"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.user.is_active = False
        self.user.save()
        self.client.post(reverse("staff_portal:login"), {"username": self.user.username, "password": "Staff-test-9274!"})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_authentication_and_is_private(self):
        self.assertEqual(self.client.get(reverse("staff_portal:profile")).status_code, 302)
        self.login_staff()
        response = self.client.get(reverse("staff_portal:profile"))
        self.assertContains(response, "Pilot Staff")
        self.assertNotContains(response, "Other Staff")
        self.assertIn("no-store", response["Cache-Control"])

    def test_staff_cannot_access_cms_api_or_other_accounts(self):
        self.login_staff()
        self.assertRedirects(self.client.get("/cms-admin/"), reverse("staff_portal:profile"))
        for url in ["/cms-admin/pages/", reverse("staff_profile_dashboard"), "/api/v2/pages/", "/auth/email/"]:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.get("/staff/profile/999/").status_code, 404)

    def test_draft_and_submission_do_not_publish_or_change_official_fields(self):
        self.login_staff()
        response = self.client.post(reverse("staff_portal:profile"), {
            "action": "save", "biography": "New draft.", "name": "Hacked name", "role": "CEO", "access": self.other_access.pk,
        })
        self.assertEqual(response.status_code, 302)
        update = self.access.updates.get()
        self.assertEqual(update.status, "draft")
        self.assertEqual(update.biography, "New draft.")
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, "Pilot Staff")
        self.assertEqual(self.member.role, "Scientist")
        self.assertEqual(self.member.bio, "<p>Original biography.</p>")
        self.assertFalse(self.other_access.updates.exists())
        self.client.post(reverse("staff_portal:profile"), {"action": "submit", "biography": "Ready for review."})
        update.refresh_from_db()
        self.assertEqual(update.status, "submitted")
        self.assertIsNotNone(update.submitted_at)
        self.client.post(reverse("staff_portal:profile"), {"action": "save", "biography": "Overwrite pending."})
        update.refresh_from_db()
        self.assertEqual(update.biography, "Ready for review.")

    def test_only_reviewer_can_publish_and_publishing_preserves_account(self):
        update = self.draft()
        with self.assertRaises(ValidationError):
            review_update(update.pk, self.user, "approve", "")
        reviewed = review_update(update.pk, self.admin, "approve", "Approved.")
        self.assertEqual(reviewed.status, "approved")
        self.member.refresh_from_db()
        self.assertEqual(self.member.bio, "<p>Updated biography.</p>")
        self.access.refresh_from_db()
        self.assertEqual(self.access.member_id, self.member.pk)
        self.page.refresh_from_db()
        self.assertFalse(self.page.has_unpublished_changes)
        self.assertEqual(self.page.live_revision.as_object().staffmembers.get(id=self.member.pk).bio, self.member.bio)
        with self.assertRaises(ValidationError):
            review_update(update.pk, self.admin, "approve", "")

    def test_unpublished_page_drafts_block_approval(self):
        update = self.draft()
        self.page.save_revision()
        with self.assertRaisesMessage(ValidationError, "unpublished draft"):
            review_update(update.pk, self.admin, "approve", "")

    def test_concurrent_public_profile_edit_blocks_approval(self):
        update = self.draft()
        StaffMember.objects.filter(pk=self.member.pk).update(role="Changed role")
        with self.assertRaisesMessage(ValidationError, "public profile changed"):
            review_update(update.pk, self.admin, "approve", "")

    def test_request_changes_keeps_history_and_allows_new_submission(self):
        update = self.draft()
        review_update(update.pk, self.admin, "request_changes", "Please shorten the biography.")
        self.login_staff()
        self.assertContains(self.client.get(reverse("staff_portal:profile")), "Please shorten the biography.")
        self.client.post(reverse("staff_portal:profile"), {"action": "submit", "biography": "Short biography."})
        self.assertEqual(self.access.updates.count(), 2)
        update.refresh_from_db()
        self.assertEqual(update.status, "changes_requested")

    def test_biography_html_is_escaped_and_unsafe_links_are_rejected(self):
        update = self.draft()
        update.biography = '<script>alert("bad")</script>'
        update.save()
        review_update(update.pk, self.admin, "approve", "")
        self.member.refresh_from_db()
        self.assertNotIn("<script>", self.member.bio)
        self.assertIn("&lt;script&gt;", self.member.bio)
        form = StaffProfileForm({"website": "javascript:alert(1)"})
        self.assertFalse(form.is_valid())

    def test_private_photo_is_only_visible_to_owner_or_reviewer(self):
        update = self.draft(photo_data=b"private-photo")
        url = reverse("staff_portal:photo", args=[update.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login_staff()
        response = self.client.get(url)
        self.assertEqual(response.content, b"private-photo")
        self.assertIn("no-store", response["Cache-Control"])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_photo_upload_is_private_until_approved(self):
        output = BytesIO()
        Image.new("RGB", (80, 80), "green").save(output, "PNG")
        self.login_staff()
        count = get_image_model().objects.count()
        self.client.post(reverse("staff_portal:profile"), {
            "action": "submit", "biography": "With photo.",
            "photo": SimpleUploadedFile("portrait.png", output.getvalue(), content_type="image/png"),
        })
        update = self.access.updates.get()
        self.assertTrue(bytes(update.photo_data).startswith(b"\xff\xd8"))
        self.assertEqual(get_image_model().objects.count(), count)
        review_update(update.pk, self.admin, "approve", "")
        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.photo)
        self.assertEqual(get_image_model().objects.count(), count + 1)

    def test_invalid_upload_is_rejected(self):
        form = StaffProfileForm({}, {"photo": SimpleUploadedFile("script.svg", b"<svg><script/></svg>", content_type="image/svg+xml")})
        self.assertFalse(form.is_valid())

    def test_admin_screens_render_and_regular_accounts_are_denied(self):
        update = self.draft()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("staff_profile_dashboard")), "Send invitation")
        self.assertContains(self.client.get(reverse("staff_profile_review", args=[update.pk])), "Submitted changes")
        self.login_staff()
        self.assertEqual(self.client.post(reverse("staff_profile_review", args=[update.pk]), {"action": "approve"}).status_code, 403)

    def test_password_reset_only_emails_active_profile_accounts(self):
        url = reverse("staff_portal:password_reset")
        self.client.post(url, {"email": self.admin.email})
        self.assertEqual(len(mail.outbox), 0)
        self.client.post(url, {"email": self.user.email})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/staff/password-reset/", mail.outbox[0].body)

    def test_reset_requests_are_throttled_without_disclosing_account(self):
        url = reverse("staff_portal:password_reset")
        for _ in range(7):
            response = self.client.post(url, {"email": self.user.email})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 5)

    def test_reviewer_can_review_but_cannot_create_accounts(self):
        reviewer = get_user_model().objects.create_user(username="reviewer", password="Reviewer-password-9284!")
        reviewer.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"), Permission.objects.get(codename="access_admin"))
        group = Group.objects.create(name="Staff profile reviewers")
        reviewer.groups.add(group)
        for codename in ["change_page", "publish_page"]:
            GroupPagePermission.objects.create(group=group, page=self.page, permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename))
        self.client.force_login(reviewer)
        self.assertEqual(self.client.get(reverse("staff_profile_dashboard")).status_code, 200)
        denied = self.client.post(reverse("staff_profile_dashboard"), {"member": self.member.pk, "email": "new@example.test"})
        # Wagtail wraps PermissionDenied in a redirect to the admin home.
        self.assertEqual(denied.status_code, 302)
        self.assertEqual(denied["Location"], reverse("wagtailadmin_home"))
        self.assertFalse(get_user_model().objects.filter(email="new@example.test").exists())
        update = self.draft()
        response = self.client.post(reverse("staff_profile_review", args=[update.pk]), {"action": "approve", "comment": "Reviewed"})
        self.assertEqual(response.status_code, 302)
        update.refresh_from_db()
        self.assertEqual(update.status, "approved")

    def test_password_change_and_logout(self):
        self.login_staff()
        response = self.client.post(reverse("staff_portal:password_change"), {
            "old_password": "Staff-test-9274!", "new_password1": "Another-safe-password-9874!", "new_password2": "Another-safe-password-9874!",
        })
        self.assertRedirects(response, reverse("staff_portal:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-safe-password-9874!"))
        self.client.post(reverse("staff_portal:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_forms_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse("staff_portal:profile"), {"action": "submit"}).status_code, 403)
        access, url, _ = self.invite()
        self.assertEqual(client.post(url, {"new_password1": "safe-password"}).status_code, 403)

    def test_invitation_preserves_origin_and_enforces_csrf(self):
        access, url, _ = self.invite()
        client = Client(enforce_csrf_checks=True)
        response = client.get(url)
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertContains(response, '<meta name="referrer" content="same-origin">')
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode()).group(1)
        data = {
            "csrfmiddlewaretoken": token,
            "new_password1": "My-new-unique-password-3928!",
            "new_password2": "My-new-unique-password-3928!",
        }
        for origin in ["null", "https://untrusted.example"]:
            self.assertEqual(client.post(url, data, HTTP_ORIGIN=origin).status_code, 403)
        access.user.refresh_from_db()
        self.assertFalse(access.user.has_usable_password())
        response = client.post(url, data, HTTP_ORIGIN="http://testserver")
        self.assertRedirects(response, reverse("staff_portal:login"))
        access.user.refresh_from_db()
        self.assertTrue(access.user.check_password(data["new_password1"]))

    def test_portal_login_preserves_origin_and_accepts_csrf_post(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse("staff_portal:login")
        response = client.get(url, secure=True)
        self.assertContains(response, '<meta name="referrer" content="same-origin">')
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode()).group(1)
        response = client.post(url, {
            "csrfmiddlewaretoken": token,
            "username": self.user.email,
            "password": "Staff-test-9274!",
        }, secure=True, HTTP_ORIGIN="https://testserver")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("staff_portal:profile"))
