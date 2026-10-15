import re
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from wagtail.images import get_image_model
from wagtail.models import GroupPagePermission, Page, Site

from climweb.pages.home.tests.factories import HomePageFactory, get_or_create_homepage
from climweb.pages.organisation_pages.organisation.tests.factories import OrganisationIndexPageFactory
from .factories import StaffPageFactory
from ..forms import StaffDriveUploadForm, StaffProfileForm, StaffTrainingReportForm
from ..google_drive import ensure_staff_folder
from ..models import (
    Department,
    StaffDriveFolder,
    StaffEmployment,
    StaffMember,
    StaffPageSelection,
    StaffProfileAccess,
    StaffProfileEmailLog,
    StaffProfileUpdate,
    StaffNotificationDelivery,
    StaffTrainingAssignment,
    StaffTrainingReport,
    StaffTrainingReportDocument,
)
from ..notifications import queue_deadline_notifications, queue_training_assigned_notifications, send_staff_notification
from ..services import change_staff_employment, invite_staff, link_existing_staff_user, member_fingerprint, review_update
from ..tasks import sync_report_document_to_drive
from ..wagtail_hooks import staff_profile_permissions


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", AXES_ENABLED=False)
class StaffPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # CMS dashboard/explorer require one common tree root.
        home = HomePageFactory(parent=Page.get_first_root_node())
        site = Site.objects.get(is_default_site=True)
        site.root_page = home
        site.save()
        organisation = OrganisationIndexPageFactory(parent=home)
        cls.page = StaffPageFactory(parent=organisation)
        department = Department.objects.create(name="Research")
        cls.member = StaffMember.objects.create(page=cls.page, name="Pilot Staff", role="Scientist", department=department, bio="<p>Original biography.</p>")
        cls.other_member = StaffMember.objects.create(page=cls.page, name="Other Staff", role="Forecaster", department=department)
        StaffPageSelection.objects.create(page=cls.page, member=cls.member, sort_order=0)
        StaffPageSelection.objects.create(page=cls.page, member=cls.other_member, sort_order=1)
        cls.page.save_revision().publish()
        User = get_user_model()
        cls.admin = User.objects.create_superuser(username="staff-admin", email="admin@example.test", password="Admin-test-9274!")
        cls.user = User.objects.create_user(username="pilot@example.test", email="pilot@example.test", password="Staff-test-9274!")
        cls.access = StaffProfileAccess.objects.create(member=cls.member, user=cls.user, accepted_at=timezone.now())
        cls.other_user = User.objects.create_user(username="other@example.test", email="other@example.test", password="Other-test-9274!")
        cls.other_access = StaffProfileAccess.objects.create(member=cls.other_member, user=cls.other_user)

    def login_staff(self):
        self.client.force_login(self.user)

    def test_staff_login_uses_dashboard_branding_and_copyright(self):
        response = self.client.get(reverse("staff_portal:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="portal-auth-brand-mark"')
        self.assertContains(response, "Staff workspace")
        self.assertContains(response, f"© {timezone.localdate().year} ACMAD. All rights reserved.")
        self.assertContains(response, "Sign in to your workspace")

    def training_assignment(self, member=None, **kwargs):
        today = timezone.localdate()
        values = {
            "member": member or self.member,
            "title": "Regional climate workshop",
            "organizer": "ACMAD",
            "start_date": today,
            "end_date": today + timedelta(days=2),
            "report_due_date": today + timedelta(days=9),
            "assigned_by": self.admin,
        }
        values.update(kwargs)
        return StaffTrainingAssignment.objects.create(**values)

    def test_hr_reviewer_permission_is_available_in_wagtail_groups(self):
        permissions = staff_profile_permissions()
        self.assertEqual(list(permissions.values_list("codename", flat=True)), ["review_staff_profiles"])

    @override_settings(GOOGLE_DRIVE_ENABLED=False)
    def test_staff_dashboard_shows_only_own_training_and_drive_state(self):
        assignment = self.training_assignment()
        self.training_assignment(member=self.other_member, title="Other staff workshop")
        self.login_staff()
        response = self.client.get(reverse("staff_portal:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, assignment.title)
        self.assertNotContains(response, "Other staff workshop")
        self.assertContains(response, "Google Drive")
        self.assertContains(response, "Not configured")
        content = response.content.decode()
        menu_labels = ["Dashboard", "Activities &amp; Reports", "Drive", "My Profile"]
        menu_positions = [content.index(label) for label in menu_labels]
        self.assertEqual(menu_positions, sorted(menu_positions))
        self.assertContains(response, '<svg viewBox="0 0 24 24"', count=6)

    @override_settings(
        GOOGLE_DRIVE_ENABLED=True,
        GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE="/run/secrets/test.json",
        GOOGLE_DRIVE_SHARED_DRIVE_ID="sharedDrive123",
        GOOGLE_DRIVE_ROOT_FOLDER_ID="rootFolder123",
    )
    @patch("climweb.pages.organisation_pages.staff.views.breadcrumbs")
    @patch("climweb.pages.organisation_pages.staff.views.list_items")
    @patch("climweb.pages.organisation_pages.staff.views.assert_within_root")
    @patch("climweb.pages.organisation_pages.staff.views._drive_access")
    def test_staff_can_browse_scoped_drive_folder(self, access, within_root, items, crumbs):
        service = object()
        access.return_value = (service, "staffRoot123", self.member)
        within_root.return_value = {
            "id": "staffRoot123",
            "name": "Pilot Staff",
            "mimeType": "application/vnd.google-apps.folder",
        }
        items.return_value = ([{
            "id": "document123",
            "name": "Workshop notes.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }], "")
        crumbs.return_value = [{"id": "staffRoot123", "name": "Pilot Staff"}]
        self.login_staff()
        response = self.client.get(reverse("staff_portal:drive_files"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workshop notes.docx")
        self.assertContains(response, "<h1>Drive</h1>", html=True)
        self.assertNotContains(response, "Create folder")
        self.assertContains(response, reverse("staff_portal:drive_download", args=["document123"]))
        within_root.assert_called_once_with(service, "staffRoot123", "staffRoot123")

    @override_settings(
        GOOGLE_DRIVE_ENABLED=True,
        GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE="/run/secrets/test.json",
        GOOGLE_DRIVE_SHARED_DRIVE_ID="sharedDrive123",
        GOOGLE_DRIVE_ROOT_FOLDER_ID="rootFolder123",
    )
    @patch("climweb.pages.organisation_pages.staff.views.record_audit")
    @patch("climweb.pages.organisation_pages.staff.views.upload_file")
    @patch("climweb.pages.organisation_pages.staff.views.assert_within_root")
    @patch("climweb.pages.organisation_pages.staff.views.ensure_staff_folder")
    @patch("climweb.pages.organisation_pages.staff.views.get_drive_service")
    def test_drive_upload_is_forced_into_the_users_dedicated_folder(
        self, service_factory, ensure_folder, within_root, upload, record_audit
    ):
        service = object()
        service_factory.return_value = service
        ensure_folder.return_value = "personalFolder123"
        within_root.return_value = {"id": "personalFolder123", "mimeType": "application/vnd.google-apps.folder"}
        upload.return_value = {"id": "uploadedFile123", "name": "notes.pdf"}
        self.login_staff()
        response = self.client.post(reverse("staff_portal:drive_upload"), {
            "folder_id": "anotherFolder123",
            "files": SimpleUploadedFile("notes.pdf", b"notes", content_type="application/pdf"),
        })
        self.assertRedirects(
            response,
            reverse("staff_portal:drive_files") + "?folder=personalFolder123",
            fetch_redirect_response=False,
        )
        ensure_folder.assert_called_once_with(service, self.member, self.user)
        within_root.assert_called_once_with(service, "personalFolder123", "personalFolder123")
        upload.assert_called_once()
        self.assertEqual(upload.call_args.args[1], "personalFolder123")

    @override_settings(
        GOOGLE_DRIVE_ENABLED=True,
        GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE="/run/secrets/test.json",
        GOOGLE_DRIVE_SHARED_DRIVE_ID="sharedDrive123",
        GOOGLE_DRIVE_ROOT_FOLDER_ID="rootFolder123",
    )
    @patch("climweb.pages.organisation_pages.staff.views.assert_within_root", side_effect=PermissionDenied)
    @patch("climweb.pages.organisation_pages.staff.views._drive_access", return_value=(object(), "staffRoot123", None))
    def test_staff_cannot_browse_outside_scoped_drive_folder(self, access, within_root):
        self.login_staff()
        response = self.client.get(reverse("staff_portal:drive_files") + "?folder=anotherFolder123")
        self.assertEqual(response.status_code, 403)

    def test_drive_upload_form_limits_file_count_and_size(self):
        files = [SimpleUploadedFile(f"file-{index}.txt", b"content") for index in range(11)]
        form = StaffDriveUploadForm({"folder_id": "staffRoot123"}, {"files": files})
        self.assertFalse(form.is_valid())
        self.assertIn("no more than 10", str(form.errors["files"]))

    @override_settings(GOOGLE_DRIVE_ROOT_FOLDER_ID="rootFolder123")
    @patch("climweb.pages.organisation_pages.staff.google_drive.record_audit")
    @patch("climweb.pages.organisation_pages.staff.google_drive.rename_item")
    @patch("climweb.pages.organisation_pages.staff.google_drive.assert_within_root")
    @patch("climweb.pages.organisation_pages.staff.google_drive.get_item")
    def test_existing_staff_drive_folder_is_renamed_to_staff_name_only(
        self, get_item, within_root, rename, record_audit
    ):
        StaffDriveFolder.objects.create(member=self.member, folder_id="personalFolder123")
        get_item.return_value = {
            "id": "personalFolder123",
            "name": f"{self.member.name} — Staff {self.member.pk}",
            "mimeType": "application/vnd.google-apps.folder",
        }
        rename.return_value = {
            "id": "personalFolder123",
            "name": self.member.name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        service = object()
        self.assertEqual(ensure_staff_folder(service, self.member, self.user), "personalFolder123")
        rename.assert_called_once_with(service, "personalFolder123", self.member.name)

    def test_staff_can_save_and_submit_assigned_training_report(self):
        self.other_user.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"))
        assignment = self.training_assignment()
        self.login_staff()
        url = reverse("staff_portal:training_report", args=[assignment.pk])
        response = self.client.post(url, {"action": "save", "title": "Workshop report", "summary": "Draft summary"})
        self.assertRedirects(response, url)
        report = StaffTrainingReport.objects.get(assignment=assignment)
        self.assertEqual(report.status, StaffTrainingReport.Status.DRAFT)
        response = self.client.post(url, {"action": "submit", "title": "Workshop report", "summary": "Final summary"})
        self.assertRedirects(response, url)
        report.refresh_from_db()
        self.assertEqual(report.status, StaffTrainingReport.Status.SUBMITTED)
        self.assertIsNotNone(report.submitted_at)
        delivery = StaffNotificationDelivery.objects.get(
            event=StaffNotificationDelivery.Event.REPORT_SUBMITTED,
            report=report,
            recipient=self.other_user.email,
        )
        self.assertFalse(
            StaffNotificationDelivery.objects.filter(
                event=StaffNotificationDelivery.Event.REPORT_SUBMITTED,
                report=report,
                recipient=self.admin.email,
            ).exists()
        )
        with patch(
            "climweb.pages.organisation_pages.staff.notifications._email_logo_url",
            return_value="https://example.test/media/acmad-logo.png",
        ):
            send_staff_notification(delivery.pk)
        self.assertEqual(mail.outbox[-1].to, [self.other_user.email])
        self.assertIn("awaiting review", mail.outbox[-1].subject)
        self.assertIn(reverse("staff_portal:hr_review_training_report", args=[report.pk]), mail.outbox[-1].body)
        self.assertNotIn(reverse("staff_training_report_review", args=[report.pk]), mail.outbox[-1].body)
        self.assertNotIn("This is an automated message", mail.outbox[-1].body)
        html = mail.outbox[-1].alternatives[0][0]
        self.assertIn('src="https://example.test/media/acmad-logo.png"', html)
        self.assertNotIn("This is an automated message", html)

    def test_training_nomination_email_uses_staff_account_and_authenticated_link(self):
        assignment = self.training_assignment()
        deliveries = queue_training_assigned_notifications([assignment])
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].recipient, self.user.email)
        self.assertTrue(send_staff_notification(deliveries[0].pk))
        self.assertEqual(mail.outbox[-1].to, [self.user.email])
        self.assertIn("Activity assignment", mail.outbox[-1].subject)
        self.assertIn(reverse("staff_portal:training_report", args=[assignment.pk]), mail.outbox[-1].body)

    def test_deadline_reminders_are_deduplicated(self):
        today = timezone.localdate()
        assignment = self.training_assignment(report_due_date=today + timedelta(days=2))
        self.assertEqual(queue_deadline_notifications(today), 1)
        self.assertEqual(queue_deadline_notifications(today), 0)
        delivery = StaffNotificationDelivery.objects.get(
            assignment=assignment,
            event=StaffNotificationDelivery.Event.REPORT_DUE_2_DAYS,
        )
        send_staff_notification(delivery.pk)
        self.assertIn("due in 2 days", mail.outbox[-1].subject)

    def test_overdue_reminders_are_sent_daily_and_deduplicated_per_day(self):
        today = timezone.localdate()
        assignment = self.training_assignment(report_due_date=today - timedelta(days=3))
        self.assertEqual(queue_deadline_notifications(today), 1)
        self.assertEqual(queue_deadline_notifications(today), 0)
        self.assertEqual(queue_deadline_notifications(today + timedelta(days=1)), 1)
        self.assertEqual(
            StaffNotificationDelivery.objects.filter(
                assignment=assignment,
                event=StaffNotificationDelivery.Event.REPORT_OVERDUE,
            ).count(),
            2,
        )

    def test_staff_cannot_open_another_members_training_report(self):
        assignment = self.training_assignment(member=self.other_member)
        self.login_staff()
        self.assertEqual(self.client.get(reverse("staff_portal:training_report", args=[assignment.pk])).status_code, 404)

    def test_reviewer_can_assign_multiple_staff_and_approve_submitted_report(self):
        self.client.force_login(self.admin)
        assignment_url = reverse("staff_training_assign")
        form_response = self.client.get(assignment_url)
        self.assertContains(form_response, 'data-searchable-multiselect="true"')
        self.assertContains(form_response, "staff/js/searchable_multiselect.js")
        self.assertNotIn("status", form_response.context["form"].fields)
        today = timezone.localdate()
        response = self.client.post(assignment_url, {
            "member": [self.member.pk, self.other_member.pk],
            "activity_type": StaffTrainingAssignment.ActivityType.WORKSHOP,
            "title": "Hydrology training",
            "organizer": "WMO",
            "start_date": today,
            "end_date": today + timedelta(days=1),
            "report_due_date": today + timedelta(days=5),
            "status": StaffTrainingAssignment.Status.NOMINATED,
        })
        self.assertRedirects(response, reverse("staff_profile_dashboard"))
        self.assertEqual(StaffTrainingAssignment.objects.filter(title="Hydrology training").count(), 2)
        assignment = StaffTrainingAssignment.objects.get(title="Hydrology training", member=self.member)
        self.assertEqual(assignment.activity_type, StaffTrainingAssignment.ActivityType.WORKSHOP)
        report = StaffTrainingReport.objects.create(
            assignment=assignment,
            title="Hydrology report",
            summary="Lessons learned",
            status=StaffTrainingReport.Status.SUBMITTED,
            submitted_at=timezone.now(),
        )
        response = self.client.post(reverse("staff_training_report_review", args=[report.pk]), {"action": "approve"})
        self.assertRedirects(response, reverse("staff_profile_dashboard"))
        report.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(report.status, StaffTrainingReport.Status.APPROVED)
        self.assertIsNotNone(report.approved_at)
        self.assertEqual(assignment.status, StaffTrainingAssignment.Status.COMPLETED)
        delivery = StaffNotificationDelivery.objects.get(
            report=report,
            event=StaffNotificationDelivery.Event.REPORT_APPROVED,
        )
        send_staff_notification(delivery.pk)
        self.assertEqual(mail.outbox[-1].to, [self.user.email])
        self.assertIn("approved", mail.outbox[-1].subject)

    def test_changes_requested_email_contains_hr_comment(self):
        assignment = self.training_assignment()
        report = StaffTrainingReport.objects.create(
            assignment=assignment,
            title="Workshop report",
            summary="Initial submission",
            status=StaffTrainingReport.Status.SUBMITTED,
            submitted_at=timezone.now(),
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("staff_training_report_review", args=[report.pk]),
            {"action": "request_changes", "comment": "Please add the agreed follow-up actions."},
        )
        self.assertRedirects(response, reverse("staff_profile_dashboard"))
        delivery = StaffNotificationDelivery.objects.get(
            report=report,
            event=StaffNotificationDelivery.Event.REPORT_CHANGES_REQUESTED,
        )
        send_staff_notification(delivery.pk)
        self.assertEqual(mail.outbox[-1].to, [self.user.email])
        self.assertIn("Please add the agreed follow-up actions.", mail.outbox[-1].body)

    def test_linked_hr_user_can_manage_reports_from_staff_workspace(self):
        self.user.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"))
        self.login_staff()
        dashboard_url = reverse("staff_portal:hr_dashboard")
        response = self.client.get(reverse("staff_portal:dashboard"))
        self.assertNotContains(response, "HR Management")
        hr_dashboard = self.client.get(dashboard_url)
        self.assertContains(hr_dashboard, "HR Dashboard")
        self.assertNotContains(hr_dashboard, "CMS dashboard")
        self.assertContains(
            hr_dashboard,
            f'href="{reverse("staff_portal:dashboard")}#training"',
        )
        self.assertContains(hr_dashboard, ">Activities &amp; Reports</a>", html=False)
        assignment_url = reverse("staff_portal:hr_assign_training")
        assignment_form = self.client.get(assignment_url)
        self.assertContains(assignment_form, 'data-searchable-multiselect="true"')
        self.assertContains(assignment_form, "staff/js/searchable_multiselect.js")
        self.assertNotIn("status", assignment_form.context["form"].fields)

        today = timezone.localdate()
        response = self.client.post(assignment_url, {
            "member": self.other_member.pk,
            "activity_type": StaffTrainingAssignment.ActivityType.WORKSHOP,
            "title": "Portal-managed workshop",
            "organizer": "ACMAD",
            "start_date": today,
            "end_date": today + timedelta(days=1),
            "report_due_date": today + timedelta(days=4),
            "status": StaffTrainingAssignment.Status.CANCELLED,
        })
        self.assertRedirects(response, dashboard_url)
        assignment = StaffTrainingAssignment.objects.get(title="Portal-managed workshop")
        self.assertEqual(assignment.status, StaffTrainingAssignment.Status.NOMINATED)
        report = StaffTrainingReport.objects.create(
            assignment=assignment,
            title="Workshop report",
            summary="Completed through the staff workspace.",
            status=StaffTrainingReport.Status.SUBMITTED,
            submitted_at=timezone.now(),
        )
        response = self.client.post(
            reverse("staff_portal:hr_review_training_report", args=[report.pk]),
            {"action": "approve", "comment": "Approved"},
        )
        self.assertRedirects(response, dashboard_url)
        report.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(report.status, StaffTrainingReport.Status.APPROVED)
        self.assertEqual(assignment.status, StaffTrainingAssignment.Status.COMPLETED)

    def test_hr_dashboard_paginates_clickable_lists_by_five(self):
        self.user.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"))
        self.login_staff()
        today = timezone.localdate()
        for index in range(7):
            assignment = self.training_assignment(
                title=f"Paginated activity {index}",
                start_date=today + timedelta(days=index + 1),
                end_date=today + timedelta(days=index + 2),
            )
            StaffTrainingReport.objects.create(
                assignment=assignment,
                title=f"Paginated report {index}",
                summary="Ready for review",
                status=StaffTrainingReport.Status.SUBMITTED,
                submitted_at=timezone.now() + timedelta(minutes=index),
            )

        response = self.client.get(reverse("staff_portal:hr_dashboard"))
        self.assertEqual(len(response.context["training_assignments"]), 5)
        self.assertEqual(len(response.context["submitted_reports"]), 5)
        self.assertContains(response, 'class="portal-clickable-row"', count=10)
        self.assertContains(response, "Page 1 of 2", count=2)

        response = self.client.get(reverse("staff_portal:hr_dashboard"), {
            "assignments_page": 2,
            "reports_page": 2,
        })
        self.assertEqual(len(response.context["training_assignments"]), 2)
        self.assertEqual(len(response.context["submitted_reports"]), 2)

    def test_hr_can_remove_nomination_only_before_activity_starts(self):
        self.user.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"))
        self.login_staff()
        today = timezone.localdate()
        future = self.training_assignment(
            title="Future activity",
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=2),
        )
        detail_url = reverse("staff_portal:hr_training_assignment", args=[future.pk])
        remove_url = reverse("staff_portal:hr_remove_nomination", args=[future.pk])
        self.assertContains(self.client.get(detail_url), "Remove nomination")
        response = self.client.post(remove_url)
        self.assertRedirects(response, detail_url)
        future.refresh_from_db()
        self.assertEqual(future.status, StaffTrainingAssignment.Status.CANCELLED)
        delivery = StaffNotificationDelivery.objects.get(
            assignment=future,
            event=StaffNotificationDelivery.Event.ACTIVITY_NOMINATION_REMOVED,
        )
        self.assertEqual(delivery.recipient, self.user.email)
        self.assertTrue(send_staff_notification(delivery.pk))
        self.assertIn("nomination removed", mail.outbox[-1].subject.lower())
        self.assertIn("no longer expected to attend", mail.outbox[-1].body)
        self.assertIn(reverse("staff_portal:dashboard"), mail.outbox[-1].body)
        self.assertEqual(self.client.get(remove_url).status_code, 405)

        started = self.training_assignment(title="Started activity")
        started_remove_url = reverse("staff_portal:hr_remove_nomination", args=[started.pk])
        self.client.post(started_remove_url)
        started.refresh_from_db()
        self.assertEqual(started.status, StaffTrainingAssignment.Status.NOMINATED)

    def test_training_reports_accept_docx_and_pptx_uploads(self):
        supported_files = [
            ("report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ]
        for filename, content_type in supported_files:
            with self.subTest(filename=filename):
                form = StaffTrainingReportForm(
                    {"title": "Activity report", "summary": "Summary"},
                    {"document_1": SimpleUploadedFile(filename, b"office-file", content_type=content_type)},
                )
                self.assertTrue(form.is_valid(), form.errors)

    def test_training_report_has_three_distinct_document_fields_without_drive_link(self):
        uploads = {
            f"document_{index}": SimpleUploadedFile(
                f"document-{index}.pdf",
                b"pdf",
                content_type="application/pdf",
            )
            for index in range(1, 4)
        }
        form = StaffTrainingReportForm({"title": "Activity report", "summary": "Summary"}, uploads)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            [field for field in form.fields if field.startswith("document_")],
            ["document_1", "document_2", "document_3"],
        )
        self.assertNotIn("documents", form.fields)
        self.assertNotIn("drive_file_url", form.fields)

        assignment = self.training_assignment()
        self.login_staff()
        response = self.client.get(reverse("staff_portal:training_report", args=[assignment.pk]))
        for field_name in ["document_1", "document_2", "document_3"]:
            self.assertContains(response, f'name="{field_name}"')
        self.assertNotContains(response, "Google Drive file link")
        self.assertNotContains(response, "Open Drive")

    def test_staff_can_upload_and_download_three_report_documents(self):
        assignment = self.training_assignment()
        self.login_staff()
        uploads = [
            SimpleUploadedFile(f"supporting-{index}.pdf", f"file-{index}".encode(), content_type="application/pdf")
            for index in range(1, 4)
        ]
        file_field = StaffTrainingReportDocument._meta.get_field("file")
        with tempfile.TemporaryDirectory() as upload_root, patch.object(
            file_field,
            "storage",
            FileSystemStorage(location=upload_root),
        ):
            response = self.client.post(
                reverse("staff_portal:training_report", args=[assignment.pk]),
                {
                    "action": "save",
                    "title": "Activity report",
                    "summary": "Summary",
                    "document_1": uploads[0],
                    "document_2": uploads[1],
                    "document_3": uploads[2],
                },
            )
            self.assertRedirects(response, reverse("staff_portal:training_report", args=[assignment.pk]))
            report = StaffTrainingReport.objects.get(assignment=assignment)
            self.assertEqual(report.documents.count(), 3)
            document = report.documents.first()
            response = self.client.get(reverse("staff_portal:training_report_download", args=[document.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"file-1")
            self.assertIn(document.original_name, response["Content-Disposition"])

    @override_settings(
        GOOGLE_DRIVE_ENABLED=True,
        GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE="/run/secrets/test.json",
        GOOGLE_DRIVE_SHARED_DRIVE_ID="sharedDrive123",
        GOOGLE_DRIVE_ROOT_FOLDER_ID="rootFolder123",
    )
    @patch("climweb.pages.organisation_pages.staff.tasks.record_audit")
    @patch("climweb.pages.organisation_pages.staff.tasks.upload_file")
    @patch("climweb.pages.organisation_pages.staff.tasks.ensure_staff_folder")
    @patch("climweb.pages.organisation_pages.staff.tasks.get_drive_service")
    def test_report_document_syncs_to_the_staff_dedicated_drive_folder(
        self, service_factory, ensure_folder, upload, record_audit
    ):
        report = StaffTrainingReport.objects.create(
            assignment=self.training_assignment(), title="Activity report", summary="Summary"
        )
        file_field = StaffTrainingReportDocument._meta.get_field("file")
        with tempfile.TemporaryDirectory() as upload_root, patch.object(
            file_field, "storage", FileSystemStorage(location=upload_root)
        ):
            document = StaffTrainingReportDocument.objects.create(
                report=report,
                file=SimpleUploadedFile("report.pdf", b"report", content_type="application/pdf"),
                original_name="report.pdf",
            )
            service = object()
            service_factory.return_value = service
            ensure_folder.return_value = "personalFolder123"
            upload.return_value = {"id": "driveReport123", "name": "report.pdf"}
            result = sync_report_document_to_drive.run(document.pk, self.user.pk)
        self.assertEqual(result, "driveReport123")
        document.refresh_from_db()
        self.assertEqual(document.drive_file_id, "driveReport123")
        self.assertEqual(document.drive_sync_status, StaffTrainingReportDocument.DriveSyncStatus.SYNCED)
        ensure_folder.assert_called_once_with(service, self.member, self.user)
        self.assertEqual(upload.call_args.args[1], "personalFolder123")

    def test_existing_documents_count_toward_limit_and_can_be_removed(self):
        report = StaffTrainingReport.objects.create(
            assignment=self.training_assignment(),
            title="Activity report",
            summary="Summary",
        )
        existing = [
            StaffTrainingReportDocument.objects.create(
                report=report,
                file=f"staff-training-reports/existing-{index}.pdf",
                original_name=f"existing-{index}.pdf",
            )
            for index in range(2)
        ]
        new_files = {
            "document_1": SimpleUploadedFile("new-1.pdf", b"pdf", content_type="application/pdf"),
            "document_2": SimpleUploadedFile("new-2.pdf", b"pdf", content_type="application/pdf"),
        }
        form = StaffTrainingReportForm(
            {"title": report.title, "summary": report.summary},
            new_files,
            instance=report,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("no more than 3 documents", form.non_field_errors()[0])
        form = StaffTrainingReportForm(
            {
                "title": report.title,
                "summary": report.summary,
                "remove_documents": [existing[0].pk],
            },
            new_files,
            instance=report,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def unlinked_member(self):
        return StaffMember.objects.create(page=self.page, name="Existing Account Staff", role="Scientist", department=self.member.department)

    def test_link_existing_admin_preserves_password_groups_and_dashboard_access(self):
        member = self.unlinked_member()
        group = Group.objects.create(name="Existing admin group")
        self.admin.groups.add(group)
        password = self.admin.password
        access = link_existing_staff_user(member.pk, self.admin.pk, self.admin)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, password)
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.groups.filter(pk=group.pk).exists())
        self.assertFalse(access.profile_only)
        self.assertEqual(access.linked_by, self.admin)
        self.assertIsNotNone(access.linked_at)
        self.assertEqual(access.invitation_digest, "")
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/cms-admin/").status_code, 200)
        self.assertContains(self.client.get(reverse("staff_portal:profile")), member.name)
        self.assertNotContains(self.client.get(reverse("staff_portal:profile")), "CMS dashboard")

    def test_link_existing_editor_retains_permissions_and_can_login_by_email(self):
        member = self.unlinked_member()
        user = get_user_model().objects.create_user(username="legacy-editor", email="editor@example.test", password="Editor-safe-9274!")
        permission = Permission.objects.get(codename="access_admin")
        user.user_permissions.add(permission)
        password = user.password
        access = link_existing_staff_user(member.pk, user.pk, self.admin)
        response = self.client.post(reverse("staff_portal:login"), {"username": "EDITOR@example.test", "password": "Editor-safe-9274!"})
        self.assertRedirects(response, reverse("staff_portal:profile"))
        user.refresh_from_db()
        self.assertEqual(user.username, "legacy-editor")
        self.assertEqual(user.password, password)
        self.assertTrue(user.has_perm("wagtailadmin.access_admin"))
        self.assertFalse(user.has_perm("staff.review_staff_profiles"))
        self.assertEqual(self.client.get("/cms-admin/").status_code, 200)
        self.assertFalse(access.profile_only)

    def test_link_regular_account_does_not_grant_cms_permissions(self):
        member = self.unlinked_member()
        user = get_user_model().objects.create_user(username="existing-regular", email="regular@example.test")
        user.set_unusable_password()
        user.save()
        access = link_existing_staff_user(member.pk, user.pk, self.admin)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.has_perm("wagtailadmin.access_admin"))
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("staff_portal:profile")), member.name)
        self.assertNotContains(self.client.get(reverse("staff_portal:profile")), "CMS dashboard")
        self.assertFalse(access.profile_only)

    def test_link_form_requires_confirmation_and_does_not_send_invitation(self):
        member = self.unlinked_member()
        self.client.force_login(self.admin)
        url = reverse("staff_profile_link_user", args=[member.pk])
        self.assertContains(self.client.get(reverse("staff_profile_dashboard")), url)
        self.assertContains(self.client.get(url), "Link existing user")
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())
        response = self.client.post(url, {"user": self.admin.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())
        response = self.client.post(url, {"user": self.admin.pk, "confirm": "on"})
        self.assertRedirects(response, reverse("staff_profile_dashboard"))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_rejects_disabled_duplicate_and_missing_email_accounts(self):
        member = self.unlinked_member()
        User = get_user_model()
        disabled = User.objects.create_user(username="disabled-existing", email="disabled@example.test", is_active=False)
        missing = User.objects.create_user(username="no-email")
        duplicate = User.objects.create_user(username="duplicate-email", email=self.admin.email.upper())
        for user in [disabled, missing, duplicate]:
            with self.assertRaises(ValidationError):
                link_existing_staff_user(member.pk, user.pk, self.admin)
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())

    def test_link_cannot_replace_existing_link_or_reuse_an_account(self):
        member = self.unlinked_member()
        with self.assertRaises(ValidationError):
            link_existing_staff_user(self.member.pk, self.admin.pk, self.admin)
        with self.assertRaises(ValidationError):
            link_existing_staff_user(member.pk, self.user.pk, self.admin)
        self.access.refresh_from_db()
        self.assertEqual(self.access.user_id, self.user.pk)
        self.assertTrue(self.access.profile_only)

    def test_link_cannot_attach_former_staff(self):
        member = self.unlinked_member()
        self.offboard(member)
        with self.assertRaises(ValidationError):
            link_existing_staff_user(member.pk, self.admin.pk, self.admin)
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())

    def test_link_is_superuser_only_and_csrf_protected(self):
        member = self.unlinked_member()
        url = reverse("staff_profile_link_user", args=[member.pk])
        with self.assertRaises(ValidationError):
            link_existing_staff_user(member.pk, self.admin.pk, self.user)
        reviewer = get_user_model().objects.create_user(username="link-reviewer")
        reviewer.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"), Permission.objects.get(codename="access_admin"))
        self.client.force_login(reviewer)
        response = self.client.post(url, {"user": self.admin.pk, "confirm": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("wagtailadmin_home"))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(url, {"user": self.admin.pk, "confirm": "on"}).status_code, 403)
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())

    def test_linked_admin_offboarding_preserves_cms_but_blocks_profile(self):
        member = self.unlinked_member()
        link_existing_staff_user(member.pk, self.admin.pk, self.admin)
        self.offboard(member)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/cms-admin/").status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_portal:profile")).status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_linked_admin_cms_root_is_not_intercepted_by_profile_middleware(self):
        from django.http import HttpResponse
        from ..middleware import StaffPortalRestrictionMiddleware
        member = self.unlinked_member()
        link_existing_staff_user(member.pk, self.admin.pk, self.admin)
        request = RequestFactory().get("/cms-admin/")
        request.user = get_user_model().objects.get(pk=self.admin.pk)
        # Also verify root pass-through independently of CMS page rendering.
        middleware = StaffPortalRestrictionMiddleware(lambda request: HttpResponse("CMS root reached"))
        self.assertEqual(middleware(request).content, b"CMS root reached")

    def test_linked_existing_user_gets_my_profile_cms_menu(self):
        from ..wagtail_hooks import MyStaffProfileMenuItem
        item = MyStaffProfileMenuItem("My Staff Profile", reverse("staff_portal:profile"))
        request = RequestFactory().get("/cms-admin/")
        request.user = self.admin
        self.assertFalse(item.is_shown(request))
        member = self.unlinked_member()
        link_existing_staff_user(member.pk, self.admin.pk, self.admin)
        request.user = get_user_model().objects.get(pk=self.admin.pk)
        self.assertTrue(item.is_shown(request))
        self.offboard(member)
        self.assertFalse(item.is_shown(request))

    def test_new_contact_fields_follow_review_and_do_not_change_login_email(self):
        self.login_staff()
        data = {"action": "submit", "biography": "My updated profile", "github": "https://github.com/staff-test",
                "publications": "https://example.test/papers", "public_email": "public@example.test"}
        self.client.post(reverse("staff_portal:profile"), data)
        update = self.access.updates.get()
        self.member.refresh_from_db()
        self.assertEqual(self.member.github, "")
        self.assertEqual(update.public_email, "")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_profile_review", args=[update.pk]))
        for field in ["github", "publications"]:
            self.assertContains(response, data[field])
        review_update(update.pk, self.admin, "approve", "")
        self.member.refresh_from_db()
        self.user.refresh_from_db()
        for field in ["github", "publications"]:
            self.assertEqual(getattr(self.member, field), data[field])
        self.assertEqual(self.user.email, "pilot@example.test")
        self.login_staff()
        response = self.client.get(reverse("staff_portal:profile"))
        self.assertEqual(response.context["form"].initial["github"], data["github"])
        self.client.post(reverse("staff_portal:profile"), {"action": "submit"})
        update = self.access.updates.get(status="submitted")
        review_update(update.pk, self.admin, "approve", "")
        self.member.refresh_from_db()
        self.assertEqual(self.member.public_email, "")

    def test_new_contact_fields_can_be_set_on_creation(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data(
            github="https://github.com/new-staff", publications="https://example.test/papers", public_email="contact@example.test"))
        self.assertEqual(response.status_code, 302)
        member = StaffMember.objects.get(name="New Staff")
        self.assertEqual(member.github, "https://github.com/new-staff")
        self.assertEqual(member.publications, "https://example.test/papers")
        self.assertEqual(member.public_email, "")

    def test_contact_fields_validate_links_and_email(self):
        form = StaffProfileForm({"github": "javascript:alert(1)", "publications": "data:text/html,test", "public_email": "not-an-email"})
        self.assertFalse(form.is_valid())
        for field in ["github", "publications"]:
            self.assertIn(field, form.errors)
        self.assertNotIn("public_email", form.fields)

    def test_changed_public_contact_details_block_stale_approval(self):
        update = self.draft()
        StaffMember.objects.filter(pk=self.member.pk).update(public_email="changed@example.test")
        with self.assertRaisesMessage(ValidationError, "public profile changed"):
            review_update(update.pk, self.admin, "approve", "")

    def test_public_page_uses_registered_email_not_legacy_contact_email(self):
        StaffMember.objects.filter(pk=self.member.pk).update(public_email="legacy@example.test")
        response = self.client.get(self.page.get_url())
        self.assertContains(response, f'href="mailto:{self.user.email}"', count=2)
        self.assertNotContains(response, "legacy@example.test")

    def test_page_editor_has_selection_only_staff_formset(self):
        form_class = self.page.get_edit_handler().get_form_class()
        self.assertIn("selected_staff", form_class.formsets)
        self.assertNotIn("staffmembers", form_class.formsets)
        fields = form_class.formsets["selected_staff"].form.base_fields
        self.assertIn("member", fields)
        for field in ["name", "role", "bio", "photo", "github", "publications", "public_email"]:
            self.assertNotIn(field, fields)

    def test_page_deselection_preserves_staff_account_and_history(self):
        update = self.draft()
        page = type(self.page).objects.get(pk=self.page.pk)
        page.selected_staff.set([entry for entry in page.selected_staff.all() if entry.member_id != self.member.pk])
        page.save_revision().publish()
        cache.clear()
        self.assertNotContains(self.client.get(self.page.get_url()), "Pilot Staff")
        self.access.refresh_from_db()
        update.refresh_from_db()
        self.assertTrue(StaffMember.objects.filter(pk=self.member.pk).exists())
        self.assertTrue(self.user.is_active)
        self.assertEqual(update.status, "submitted")

    def test_empty_selection_displays_no_staff_and_reordering_is_respected(self):
        page = type(self.page).objects.get(pk=self.page.pk)
        entries = list(page.selected_staff.all())
        entries[0].sort_order, entries[1].sort_order = 1, 0
        page.selected_staff.set(entries)
        page.save_revision().publish()
        page.refresh_from_db()
        self.assertEqual([member.pk for member in page.current_staffmembers], [self.other_member.pk, self.member.pk])
        page.selected_staff.clear()
        page.save_revision().publish()
        cache.clear()
        response = self.client.get(self.page.get_url())
        self.assertNotContains(response, 'class="staff-card"')
        self.assertEqual(StaffMember.objects.filter(page=page).count(), 2)

    def test_dashboard_can_edit_details_without_changing_selection_or_email(self):
        self.client.force_login(self.admin)
        url = reverse("staff_profile_edit", args=[self.member.pk])
        response = self.client.get(url)
        self.assertContains(response, self.user.email)
        self.assertNotIn("public_email", response.context["form"].fields)
        data = dict(response.context["form"].initial)
        data.update(name="Updated official name", role="Senior Scientist", public_email="injected@example.test")
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("staff_profile_dashboard"))
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, "Updated official name")
        self.assertEqual(self.member.role, "Senior Scientist")
        self.assertEqual(self.member.registered_email, self.user.email)
        self.assertEqual(StaffPageSelection.objects.filter(page=self.page).count(), 2)
        self.assertEqual(self.member.bio, "<p>Original biography.</p>")

    def test_dashboard_edit_rejects_stale_changes_and_non_admins(self):
        self.client.force_login(self.admin)
        url = reverse("staff_profile_edit", args=[self.member.pk])
        data = dict(self.client.get(url).context["form"].initial)
        StaffMember.objects.filter(pk=self.member.pk).update(role="Changed elsewhere")
        response = self.client.post(url, data)
        self.assertContains(response, "profile changed")
        self.login_staff()
        self.assertEqual(self.client.post(url, data).status_code, 403)

    def test_registered_email_updates_invalidate_public_cache(self):
        with patch("climweb.pages.organisation_pages.staff.signals.clear_cache") as clear_public:
            with self.captureOnCommitCallbacks(execute=True):
                self.user.email = "updated@example.test"
                self.user.save(update_fields=["email"])
            clear_public.assert_called_once()
        self.assertContains(self.client.get(self.page.get_url()), 'href="mailto:updated@example.test"', count=2)

    def test_selection_migration_preserves_live_and_draft_membership(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection

        self.page.refresh_from_db()
        live_revision = self.page.live_revision
        draft_revision = self.page.save_revision()
        StaffPageSelection.objects.filter(page=self.page).delete()
        for revision in [live_revision, draft_revision]:
            content = dict(revision.content)
            content.pop("selected_staff")
            if revision.pk == draft_revision.pk:
                content["staffmembers"] = [entry for entry in content["staffmembers"] if entry["pk"] == self.other_member.pk]
            revision.content = content
            revision.save(update_fields=["content"])
        migration = import_module("climweb.pages.organisation_pages.staff.migrations.0006_staff_page_selections")
        migration.copy_staff_selections(apps, SimpleNamespace(connection=connection))
        live_revision.refresh_from_db()
        draft_revision.refresh_from_db()
        self.assertEqual([entry.member_id for entry in live_revision.as_object().selected_staff.all()], [self.member.pk, self.other_member.pk])
        self.assertEqual([entry.member_id for entry in draft_revision.as_object().selected_staff.all()], [self.other_member.pk])
        self.assertTrue(StaffProfileAccess.objects.filter(pk=self.access.pk).exists())
        self.assertEqual(StaffMember.objects.filter(page=self.page).count(), 2)

    def offboard(self, member=None, **kwargs):
        return change_staff_employment((member or self.member).pk, self.admin, "retired", timezone.localdate(), **kwargs)

    def test_offboarding_preserves_profile_history_and_account_by_default(self):
        update = self.draft(photo_data=b"retained private photo")
        self.login_staff()
        employment = self.offboard()
        self.member.refresh_from_db()
        self.user.refresh_from_db()
        update.refresh_from_db()
        self.assertEqual(self.member.bio, "<p>Original biography.</p>")
        self.assertTrue(self.user.is_active)
        self.assertEqual(update.status, "withdrawn")
        self.assertEqual(bytes(update.photo_data), b"retained private photo")
        self.assertEqual(employment.events.get().actor, self.admin)
        for url in [reverse("staff_portal:profile"), reverse("staff_portal:password_change"), reverse("staff_portal:photo", args=[update.pk])]:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(reverse("staff_portal:profile"), {"action": "submit", "biography": "Attempt"}).status_code, 403)
        with self.assertRaisesMessage(ValidationError, "Former staff"):
            review_update(update.pk, self.admin, "approve", "")

    def test_offboarding_hides_public_profile_even_after_old_revision_publish(self):
        self.page.refresh_from_db()
        old_revision = self.page.live_revision
        self.offboard()
        old_revision.publish()
        cache.clear()
        response = self.client.get(self.page.get_url())
        self.assertNotContains(response, "Pilot Staff")
        self.assertContains(response, "Other Staff")
        revision_page = old_revision.as_object()
        self.assertNotIn(self.member.pk, [member.pk for member in revision_page.current_staffmembers.all()])

    def test_offboarding_does_not_publish_pending_page_drafts(self):
        self.page.title = "Unpublished new heading"
        draft = self.page.save_revision()
        self.page.refresh_from_db()
        old_live_id = self.page.live_revision_id
        self.offboard()
        self.page.refresh_from_db()
        self.assertTrue(self.page.has_unpublished_changes)
        self.assertEqual(self.page.latest_revision_id, draft.pk)
        self.assertEqual(self.page.live_revision_id, old_live_id)

    def test_offboarding_removes_selected_and_fallback_homepage_dg_identity(self):
        StaffMember.objects.filter(pk=self.member.pk).update(name="Dr. Ousmane Ndiaye", role="Director General")
        home = get_or_create_homepage()
        home.dg_message_staff_member_id = self.member.pk
        home.save_revision().publish()
        self.assertContains(self.client.get(home.url), "Dr. Ousmane Ndiaye")
        self.offboard()
        cache.clear()
        self.assertNotContains(self.client.get(home.url), "Dr. Ousmane Ndiaye")
        home.dg_message_staff_member = None
        home.save_revision().publish()
        cache.clear()
        self.assertNotContains(self.client.get(home.url), "Dr. Ousmane Ndiaye")

    def test_offboarding_cancels_invitation_and_reactivation_requires_fresh_invite(self):
        access, url, request = self.invite()
        self.offboard(access.member)
        self.assertEqual(self.client.get(url).status_code, 400)
        with self.assertRaisesMessage(ValidationError, "Former staff"):
            invite_staff(access.member, access.user.email, request)
        change_staff_employment(access.member_id, self.admin, "active", timezone.localdate())
        self.assertEqual(self.client.get(url).status_code, 400)
        invite_staff(access.member, access.user.email, request)
        self.assertEqual(len(mail.outbox), 2)

    def test_offboarding_blocks_login_and_password_reset(self):
        self.offboard()
        response = self.client.post(reverse("staff_portal:login"), {"username": self.user.email, "password": "Staff-test-9274!"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.post(reverse("staff_portal:password_reset"), {"email": self.user.email})
        self.assertEqual(len(mail.outbox), 0)

    def test_explicit_account_disable_is_not_undone_by_reactivation(self):
        self.offboard(disable_account=True)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        employment = change_staff_employment(self.member.pk, self.admin, "active", timezone.localdate())
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.member.is_current_staff)
        self.assertEqual(employment.events.count(), 2)
        self.assertTrue(employment.events.get(status="retired").account_disabled)

    def test_reactivation_restores_public_profile_but_not_withdrawn_updates(self):
        update = self.draft()
        self.offboard()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_profile_reactivate", args=[self.member.pk]), {"confirm": "on"})
        self.assertEqual(response.status_code, 302)
        cache.clear()
        self.assertContains(self.client.get(self.page.get_url()), "Pilot Staff")
        update.refresh_from_db()
        self.assertEqual(update.status, "withdrawn")
        with self.assertRaises(ValidationError):
            review_update(update.pk, self.admin, "approve", "")

    def test_offboarding_form_requires_confirmation_and_rejects_future_dates(self):
        self.client.force_login(self.admin)
        url = reverse("staff_profile_offboard", args=[self.member.pk])
        self.assertContains(self.client.get(url), "Confirm offboarding")
        for data in [{"status": "left", "effective_date": timezone.localdate()}, {"status": "left", "effective_date": timezone.localdate() + timedelta(days=1), "confirm": "on"}]:
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            self.assertTrue(self.member.is_current_staff)
        response = self.client.post(url, {"status": "left", "effective_date": timezone.localdate(), "confirm": "on"}, follow=True)
        self.assertContains(response, "<td>Pilot Staff</td>", html=True)
        self.assertContains(response, "Profile access blocked")
        self.assertContains(self.client.get(reverse("staff_profile_dashboard")), "<td>Pilot Staff</td>", html=True)

    def test_dashboard_shows_all_staff_without_status_filters(self):
        self.offboard()
        self.client.force_login(self.admin)
        url = reverse("staff_profile_dashboard")
        for suffix in ["", "?staff_status=current", "?staff_status=former"]:
            response = self.client.get(url + suffix)
            self.assertContains(response, "<td>Pilot Staff</td>", html=True)
            self.assertContains(response, "<td>Other Staff</td>", html=True)
            self.assertNotContains(response, 'aria-label="Staff status"')
            self.assertNotContains(response, "?staff_status=")
            self.assertContains(response, "Profile access blocked")
            self.assertContains(response, reverse("staff_profile_reactivate", args=[self.member.pk]))
            self.assertNotContains(response, reverse("staff_profile_offboard", args=[self.member.pk]))
            self.assertContains(response, reverse("staff_profile_offboard", args=[self.other_member.pk]))

    def test_offboarding_is_superuser_only_csrf_protected_and_get_is_readonly(self):
        url = reverse("staff_profile_offboard", args=[self.member.pk])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(StaffEmployment.objects.exists())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(url, {"status": "left", "effective_date": timezone.localdate(), "confirm": "on"}).status_code, 403)
        self.login_staff()
        self.assertEqual(self.client.post(url, {"confirm": "on"}).status_code, 403)
        with self.assertRaises(ValidationError):
            change_staff_employment(self.member.pk, self.user, "left", timezone.localdate())
        self.assertTrue(self.member.is_current_staff)

    def test_offboarding_member_without_account_and_duplicate_action(self):
        member = StaffMember.objects.create(page=self.page, name="No Account", role="Scientist", department=self.member.department)
        self.offboard(member)
        self.assertFalse(member.is_current_staff)
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())
        with self.assertRaises(ValidationError):
            self.offboard(member)

    def test_offboarding_clears_public_caches_after_commit(self):
        with patch("climweb.pages.organisation_pages.staff.services.clear_cache") as clear_public, patch("climweb.pages.organisation_pages.staff.services.cache.clear") as clear_default:
            with self.captureOnCommitCallbacks(execute=True):
                self.offboard()
                clear_public.assert_not_called()
            clear_public.assert_called_once()
            clear_default.assert_called_once()

    def new_member_data(self, **overrides):
        return {
            "team_page": self.page.pk, "name": "New Staff", "role": "Meteorologist",
            "department": self.member.department_id, "biography": "New biography.",
            **overrides,
        }

    def test_add_member_publishes_and_preserves_existing_profiles(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("staff_profile_dashboard")), "Add staff member")
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data())
        member = StaffMember.objects.get(name="New Staff")
        self.assertRedirects(response, reverse("staff_profile_dashboard") + f"?member={member.pk}")
        self.page.refresh_from_db()
        published = self.page.live_revision.as_object().staffmembers
        self.assertEqual(published.count(), 3)
        self.assertEqual(published.get(id=member.pk).bio, "<p>New biography.</p>")
        self.assertEqual(published.get(id=self.member.pk).bio, "<p>Original biography.</p>")
        self.access.refresh_from_db()
        self.assertEqual(self.access.member_id, self.member.pk)
        self.assertFalse(self.page.has_unpublished_changes)
        self.assertFalse(StaffProfileAccess.objects.filter(member=member).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_add_member_with_invitation_creates_restricted_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data(send_invitation="on", email="NEW@example.test"))
        self.assertEqual(response.status_code, 302)
        access = StaffProfileAccess.objects.get(member__name="New Staff")
        self.assertEqual(access.user.email, "new@example.test")
        self.assertFalse(access.user.has_usable_password())
        self.assertFalse(access.user.has_perm("wagtailadmin.access_admin"))
        self.assertEqual(len(mail.outbox), 1)
        log = StaffProfileEmailLog.objects.get(member=access.member)
        self.assertEqual(log.actor, self.admin)
        self.assertEqual(log.status, StaffProfileEmailLog.Status.SENT)

    def test_dashboard_lists_staff_without_accounts_alongside_invited_staff(self):
        manual = StaffMember.objects.create(page=self.page, name="Manually added staff", role="Analyst", department=self.member.department)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_profile_dashboard"))
        self.assertCountEqual([member.pk for member in response.context["staff_members"]], [self.member.pk, self.other_member.pk, manual.pk])
        self.assertContains(response, "<td>Manually added staff</td>", html=True)
        self.assertContains(response, "<td>Not invited</td>", html=True)
        self.assertContains(response, "<td>Active</td>", html=True)
        self.assertContains(response, "<td>Invitation pending</td>", html=True)
        self.assertContains(response, reverse("staff_profile_link_user", args=[manual.pk]))
        self.assertFalse(StaffProfileAccess.objects.filter(member=manual).exists())

    def test_new_staff_without_invitation_appears_in_dashboard_table(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data(), follow=True)
        self.assertContains(response, "<td>New Staff</td>", html=True)
        self.assertContains(response, "<td>Not invited</td>", html=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_dashboard_retains_disabled_account_status(self):
        self.other_user.is_active = False
        self.other_user.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_profile_dashboard"))
        self.assertContains(response, "<td>Other Staff</td>", html=True)
        self.assertContains(response, "<td>Disabled</td>", html=True)

    def test_add_member_validates_email_before_publishing(self):
        self.client.force_login(self.admin)
        for email in ["", self.admin.email.upper()]:
            response = self.client.post(reverse("staff_profile_create"), self.new_member_data(send_invitation="on", email=email))
            self.assertEqual(response.status_code, 200)
            self.assertIn("email", response.context["form"].errors)
            self.assertFalse(StaffMember.objects.filter(name="New Staff").exists())

    def test_add_member_blocks_pending_page_draft_and_locked_page(self):
        self.client.force_login(self.admin)
        self.page.save_revision()
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data())
        self.assertContains(response, "unpublished draft")
        self.assertFalse(StaffMember.objects.filter(name="New Staff").exists())
        self.page.refresh_from_db()
        self.page.has_unpublished_changes = False
        self.page.locked = True
        self.page.save()
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data())
        self.assertContains(response, "locked")
        self.assertFalse(StaffMember.objects.filter(name="New Staff").exists())

    def test_add_member_rejects_duplicate_and_invalid_photo(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data(name=self.member.name, role=self.member.role))
        self.assertContains(response, "already exists")
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data(photo=SimpleUploadedFile("bad.png", b"not an image")))
        self.assertEqual(response.status_code, 200)
        self.assertIn("photo", response.context["form"].errors)
        self.assertEqual(StaffMember.objects.filter(page=self.page).count(), 2)

    def test_add_member_smtp_failure_preserves_profile_for_resend(self):
        self.client.force_login(self.admin)
        with patch("climweb.pages.organisation_pages.staff.services.send_mail", side_effect=OSError("SMTP unavailable")):
            response = self.client.post(reverse("staff_profile_create"), self.new_member_data(send_invitation="on", email="new@example.test"), follow=True)
        self.assertContains(response, "Do not add the staff member again")
        access = StaffProfileAccess.objects.get(member__name="New Staff")
        self.assertFalse(access.user.has_usable_password())
        self.assertContains(response, "New Staff")
        log = StaffProfileEmailLog.objects.get(member=access.member)
        self.assertEqual(log.actor, self.admin)
        self.assertEqual(log.status, StaffProfileEmailLog.Status.FAILED)

    def test_add_member_is_superuser_only_and_csrf_protected(self):
        self.login_staff()
        self.assertEqual(self.client.post(reverse("staff_profile_create"), self.new_member_data()).status_code, 403)
        reviewer = get_user_model().objects.create_user(username="creator-reviewer")
        reviewer.user_permissions.add(Permission.objects.get(codename="review_staff_profiles"), Permission.objects.get(codename="access_admin"))
        self.client.force_login(reviewer)
        self.assertNotContains(self.client.get(reverse("staff_profile_dashboard")), "Add staff member")
        response = self.client.post(reverse("staff_profile_create"), self.new_member_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("wagtailadmin_home"))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(reverse("staff_profile_create"), self.new_member_data()).status_code, 403)
        self.assertFalse(StaffMember.objects.filter(name="New Staff").exists())

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

    def test_public_allauth_pages_are_not_exposed_but_staff_login_remains(self):
        for url in ["/auth/login/", "/auth/signup/"]:
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.client.get(reverse("staff_portal:login")).status_code, 200)

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
        dashboard = self.client.get(reverse("staff_profile_dashboard"))
        self.assertContains(dashboard, "Bulk profile invitations")
        self.assertNotContains(dashboard, "Invite a staff member / resend a pending invitation")
        self.assertNotContains(dashboard, "Activity reports awaiting review")
        self.assertNotContains(dashboard, "Recent activity assignments")
        self.assertContains(self.client.get(reverse("staff_profile_review", args=[update.pk])), "Submitted changes")
        self.login_staff()
        self.assertEqual(self.client.post(reverse("staff_profile_review", args=[update.pk]), {"action": "approve"}).status_code, 403)

    def test_bulk_profile_invite_resends_pending_invites_and_reminds_active_accounts(self):
        StaffProfileUpdate.objects.create(
            access=self.other_access,
            biography="Already updated",
            status=StaffProfileUpdate.Status.APPROVED,
            source_fingerprint=member_fingerprint(self.other_member),
        )
        pending_member = StaffMember.objects.create(
            page=self.page,
            name="Pending Profile Staff",
            role="Scientist",
            department=self.member.department,
        )
        request = RequestFactory().get("/", HTTP_HOST="localhost")
        pending_access = invite_staff(pending_member, "pending-profile@example.test", request)
        first_invited_at = pending_access.invited_at
        mail.outbox.clear()

        self.client.force_login(self.admin)
        dashboard = self.client.get(reverse("staff_profile_dashboard"))
        self.assertContains(dashboard, "Bulk profile invitations")
        self.assertContains(dashboard, "Pilot Staff")
        self.assertContains(dashboard, "pilot@example.test")
        self.assertContains(dashboard, "Pending Profile Staff")
        self.assertContains(dashboard, "pending-profile@example.test")
        self.assertNotIn(self.other_access, dashboard.context["bulk_invite_candidates"])
        self.assertContains(dashboard, 'name="access_ids"', count=2)
        with patch(
            "climweb.pages.organisation_pages.staff.services._email_logo_url",
            return_value="https://example.test/media/acmad-logo.png",
        ):
            response = self.client.post(
                reverse("staff_profile_bulk_invite"),
                {"confirm": "yes", "access_ids": [self.access.pk, pending_access.pk]},
                follow=True,
            )
        self.assertContains(response, "Sent 1 invitation(s) and 1 profile reminder(s).")
        self.assertContains(response, "Profile email activity")
        self.assertContains(response, self.admin.get_username())
        self.assertContains(response, "Profile update reminder")
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            {message.subject for message in mail.outbox},
            {"Set up your ACMAD staff profile account", "Complete your ACMAD staff profile"},
        )
        self.assertTrue(all(message.alternatives for message in mail.outbox))
        self.assertTrue(all('src="https://example.test/media/acmad-logo.png"' in message.alternatives[0][0] for message in mail.outbox))
        pending_access.refresh_from_db()
        self.assertGreater(pending_access.invited_at, first_invited_at)
        logs = StaffProfileEmailLog.objects.select_related("actor", "member")
        self.assertEqual(logs.count(), 2)
        self.assertEqual({entry.actor for entry in logs}, {self.admin})
        self.assertEqual(
            {entry.event for entry in logs},
            {StaffProfileEmailLog.Event.INVITATION, StaffProfileEmailLog.Event.PROFILE_REMINDER},
        )
        self.assertTrue(all(entry.status == StaffProfileEmailLog.Status.SENT for entry in logs))

    def test_bulk_profile_invite_requires_confirmation_and_superuser(self):
        url = reverse("staff_profile_bulk_invite")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, {}, follow=True)
        self.assertContains(response, "Confirm that you want to email all eligible staff members.")
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(url, {"confirm": "yes"}, follow=True)
        self.assertContains(response, "Select at least one staff member")
        self.assertEqual(len(mail.outbox), 0)

        reviewer = get_user_model().objects.create_user(username="bulk-reviewer", password="Reviewer-password-9284!")
        reviewer.user_permissions.add(
            Permission.objects.get(codename="review_staff_profiles"),
            Permission.objects.get(codename="access_admin"),
        )
        self.client.force_login(reviewer)
        denied = self.client.post(url, {"confirm": "yes"})
        self.assertEqual(denied.status_code, 302)
        self.assertEqual(denied["Location"], reverse("wagtailadmin_home"))
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_theme_styles_are_scoped_to_admin_screens(self):
        update = self.draft()
        self.client.force_login(self.admin)
        for url in [reverse("staff_profile_dashboard"), reverse("staff_profile_create"), reverse("staff_profile_review", args=[update.pk])]:
            response = self.client.get(url)
            self.assertContains(response, 'class="nice-padding staff-admin"')
            self.assertContains(response, "staff/css/admin.css")
            self.assertLess(response.content.index(b"staff/css/portal.css"), response.content.index(b"staff/css/admin.css"))
        self.login_staff()
        response = self.client.get(reverse("staff_portal:profile"))
        self.assertNotContains(response, "staff/css/admin.css")

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
        self.assertEqual(denied.status_code, 405)
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
        logout_url = reverse("staff_portal:logout")
        response = self.client.get(logout_url)
        self.assertContains(response, "Sign out?")
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(logout_url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        logout_url = reverse("staff_portal:logout")
        self.assertEqual(client.post(logout_url).status_code, 403)
        response = client.get(logout_url)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode()).group(1)
        response = client.post(logout_url, {"csrfmiddlewaretoken": token})
        self.assertRedirects(response, reverse("staff_portal:login"))
        self.assertNotIn("_auth_user_id", client.session)

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
