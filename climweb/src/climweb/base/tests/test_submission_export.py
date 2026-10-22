import os
import shutil
import tempfile
import zipfile
from unittest import mock

import openpyxl
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import FormFileSubmission, SubmissionExportJob
from climweb.base.submission_export import build_submission_export_zip
from climweb.base.tasks import generate_submission_export
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.summer_school.tests.factories import (
    SummerSchoolIndexPageFactory,
    SummerSchoolPageFactory,
    SummerSchoolApplicationPageFactory,
)

User = get_user_model()


class SubmissionExportTestCase(WagtailPageTestCase):
    """Base class shared by the zip-builder and task tests: a page with one
    email field, one document field, and two submissions (one with a file
    attached, one without) - enough to exercise both the file-resolution
    path and the "field left blank" path in build_submission_export_zip.
    """

    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        index_page = SummerSchoolIndexPageFactory(parent=home_page)
        edition = SummerSchoolPageFactory(parent=index_page)
        cls.page = SummerSchoolApplicationPageFactory(parent=edition)

        cls.page.application_form_fields.create(
            label="Email address", field_type="email", required=True, sort_order=0,
        )
        cls.page.application_form_fields.create(
            label="Curriculum vitae", field_type="document", required=False, sort_order=1,
        )
        cls.page.save()

        cls.file_submission = FormFileSubmission.objects.create(
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 fake pdf content"),
            file_type="document",
        )

        submission_class = cls.page.get_submission_class()
        cls.with_file = submission_class.objects.create(
            page=cls.page,
            form_data={"email_address": "applicant@example.com", "curriculum_vitae": cls.file_submission.pk},
        )
        cls.without_file = submission_class.objects.create(
            page=cls.page,
            form_data={"email_address": "other@example.com", "curriculum_vitae": ""},
        )

    @classmethod
    def tearDownClass(cls):
        # FormFileSubmission.file is a real file on disk (FileSystemStorage),
        # not covered by the per-test transaction rollback - clean it up once
        # per class (not per test method) so repeated test runs don't leak
        # into the media dir, without deleting the shared cls.file_submission
        # out from under other test methods still to run in this class.
        cls.file_submission.file.delete(save=False)
        super().tearDownClass()


class TestBuildSubmissionExportZip(SubmissionExportTestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def test_zip_contains_xlsx_csv_and_the_uploaded_file(self):
        destination = os.path.join(self.tmpdir, "export.zip")

        count = build_submission_export_zip(self.page, destination)

        self.assertEqual(count, 2)
        with zipfile.ZipFile(destination) as zf:
            names = zf.namelist()
            self.assertIn("submissions.xlsx", names)
            self.assertIn("submissions.csv", names)
            file_entries = [n for n in names if n.startswith("files/")]
            self.assertEqual(len(file_entries), 1)
            # Django's storage appends a uniqueness suffix if a same-named
            # file already exists on disk (e.g. "cv_N1w4h4Z.pdf"), so assert
            # loosely on extension/prefix rather than the exact filename.
            self.assertTrue(file_entries[0].endswith(".pdf"))
            self.assertIn("cv", file_entries[0])

    def test_xlsx_row_references_the_in_zip_file_path(self):
        destination = os.path.join(self.tmpdir, "export.zip")
        build_submission_export_zip(self.page, destination)

        with zipfile.ZipFile(destination) as zf:
            with zf.open("submissions.xlsx") as f:
                workbook = openpyxl.load_workbook(f)
                sheet = workbook.active
                rows = list(sheet.iter_rows(values_only=True))

        headings = rows[0]
        cv_col = headings.index("Curriculum vitae")
        email_col = headings.index("Email address")

        data_rows = {r[email_col]: r for r in rows[1:]}
        self.assertTrue(data_rows["applicant@example.com"][cv_col].startswith("files/"))
        self.assertTrue(data_rows["applicant@example.com"][cv_col].endswith(".pdf"))
        # openpyxl reads an empty-string cell back as None on save/reload -
        # both mean "blank" here, so accept either.
        self.assertIn(data_rows["other@example.com"][cv_col], ("", None))

    def test_csv_matches_xlsx_row_count(self):
        import csv
        destination = os.path.join(self.tmpdir, "export.zip")
        build_submission_export_zip(self.page, destination)

        with zipfile.ZipFile(destination) as zf:
            with zf.open("submissions.csv") as f:
                rows = list(csv.reader(f.read().decode("utf-8").splitlines()))

        self.assertEqual(len(rows), 3)  # heading + 2 submissions

    def test_missing_file_on_disk_does_not_crash_the_export(self):
        # The FormFileSubmission row exists but the underlying file is gone
        # (e.g. manually cleaned off disk) - export must still complete for
        # every other row rather than raising. Uses its own file/submission
        # (not the shared cls.file_submission) since deleting a file isn't
        # covered by the per-test transaction rollback - it would stay
        # deleted for every other test in this class otherwise.
        orphan_file_submission = FormFileSubmission.objects.create(
            file=SimpleUploadedFile("orphan.pdf", b"%PDF-1.4 fake pdf content"), file_type="document",
        )
        submission_class = self.page.get_submission_class()
        orphan_submission = submission_class.objects.create(
            page=self.page,
            form_data={"email_address": "orphan@example.com", "curriculum_vitae": orphan_file_submission.pk},
        )
        orphan_file_submission.file.delete(save=True)

        destination = os.path.join(self.tmpdir, "export.zip")
        count = build_submission_export_zip(self.page, destination)

        self.assertEqual(count, 3)
        with zipfile.ZipFile(destination) as zf:
            file_entries = [n for n in zf.namelist() if n.startswith("files/")]
            # the shared cls.file_submission's file is still intact - only
            # the orphaned one (deliberately deleted above) should be skipped
            self.assertEqual(len(file_entries), 1)
            self.assertTrue(file_entries[0].endswith(".pdf"))
            self.assertIn("cv", file_entries[0])

        orphan_submission.delete()
        orphan_file_submission.delete()


class TestGenerateSubmissionExportTask(SubmissionExportTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="password", is_staff=True,
        )

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.settings_override = override_settings(
            PRIVATE_EXPORTS_ROOT=self.tmpdir, SUBMISSION_EXPORT_RETENTION_HOURS=48,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def test_marks_job_ready_and_emails_a_download_link(self):
        job = SubmissionExportJob.objects.create(page=self.page, requested_by=self.staff_user)

        generate_submission_export(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, SubmissionExportJob.STATUS_READY)
        self.assertEqual(job.submission_count, 2)
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, job.file_name)))

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["staff@example.com"])
        self.assertIn(job.token, sent.body)

    def test_marks_job_failed_and_notifies_requester_on_error(self):
        job = SubmissionExportJob.objects.create(page=self.page, requested_by=self.staff_user)

        with mock.patch(
            "climweb.base.submission_export.build_submission_export_zip",
            side_effect=RuntimeError("disk full"),
        ):
            with self.assertRaises(RuntimeError):
                generate_submission_export(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, SubmissionExportJob.STATUS_FAILED)
        self.assertIn("disk full", job.error_message)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("failed", mail.outbox[0].subject.lower())


class TestSubmissionExportViews(SubmissionExportTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.staff_user = User.objects.create_user(
            username="staff2", email="staff2@example.com", password="password",
            is_staff=True, is_superuser=True,
        )

    def test_request_export_view_requires_login(self):
        response = self.client.post(reverse("request_submission_export", args=[self.page.id]))
        self.assertNotEqual(response.status_code, 200)

    def test_request_export_view_enqueues_task_and_redirects(self):
        self.client.force_login(self.staff_user)

        with mock.patch("climweb.base.tasks.generate_submission_export.delay") as mocked_delay:
            response = self.client.post(reverse("request_submission_export", args=[self.page.id]))

        self.assertEqual(SubmissionExportJob.objects.filter(page=self.page, requested_by=self.staff_user).count(), 1)
        job = SubmissionExportJob.objects.get(page=self.page, requested_by=self.staff_user)
        mocked_delay.assert_called_once_with(job.id)
        self.assertRedirects(response, reverse("wagtailforms:list_submissions", args=[self.page.id]))

    def test_request_export_view_rejects_get(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("request_submission_export", args=[self.page.id]))
        self.assertEqual(response.status_code, 404)

    def test_download_view_streams_file_when_ready(self):
        self.client.force_login(self.staff_user)
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        with open(os.path.join(tmpdir, "test.zip"), "wb") as f:
            f.write(b"PK\x03\x04fake zip bytes")

        job = SubmissionExportJob.objects.create(page=self.page, requested_by=self.staff_user)
        job.mark_ready("test.zip", 21, 2, 48)

        with override_settings(PRIVATE_EXPORTS_ROOT=tmpdir):
            response = self.client.get(
                reverse("download_submission_export", args=[self.page.id, job.token])
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("test.zip", response["Content-Disposition"])

    def test_download_view_rejects_wrong_token(self):
        self.client.force_login(self.staff_user)
        job = SubmissionExportJob.objects.create(page=self.page, requested_by=self.staff_user)
        job.mark_ready("test.zip", 21, 2, 48)

        response = self.client.get(
            reverse("download_submission_export", args=[self.page.id, "not-the-real-token"])
        )
        self.assertEqual(response.status_code, 404)

    def test_download_view_shows_message_when_not_ready(self):
        self.client.force_login(self.staff_user)
        job = SubmissionExportJob.objects.create(page=self.page, requested_by=self.staff_user)

        response = self.client.get(
            reverse("download_submission_export", args=[self.page.id, job.token]), follow=True,
        )

        self.assertRedirects(response, reverse("wagtailforms:list_submissions", args=[self.page.id]))
        self.assertContains(response, "isn&#x27;t ready yet")
