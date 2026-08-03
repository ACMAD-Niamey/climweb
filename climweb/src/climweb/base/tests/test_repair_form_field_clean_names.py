import io

from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase

from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.summer_school.models import SummerSchoolApplicationFormField
from climweb.pages.summer_school.tests.factories import (
    SummerSchoolIndexPageFactory,
    SummerSchoolPageFactory,
    SummerSchoolApplicationPageFactory,
)


class TestRepairFormFieldCleanNames(WagtailPageTestCase):
    def setUp(self):
        home_page = get_or_create_homepage()
        index_page = SummerSchoolIndexPageFactory(parent=home_page)
        edition = SummerSchoolPageFactory(parent=index_page)
        self.page = SummerSchoolApplicationPageFactory(parent=edition)

        # Correct field - must be left alone.
        self.email_field = self.page.application_form_fields.create(
            label="Email address", field_type="email", required=True, sort_order=0,
        )
        # Wrong-but-nonempty clean_name - the live bug pattern: originally an
        # "Email" field, relabeled to "Gender" without clean_name following.
        self.gender_field = self.page.application_form_fields.create(
            label="Gender", field_type="dropdown", required=True, sort_order=1,
        )
        # Blank clean_name - the bulk_create/migration bypass pattern.
        self.name_field = self.page.application_form_fields.create(
            label="Full Name", field_type="singleline", required=True, sort_order=2,
        )
        self.page.save()
        for f in (self.email_field, self.gender_field, self.name_field):
            f.refresh_from_db()

        SummerSchoolApplicationFormField.objects.filter(pk=self.gender_field.pk).update(
            clean_name="email"
        )
        SummerSchoolApplicationFormField.objects.filter(pk=self.name_field.pk).update(
            clean_name=""
        )

        submission_class = self.page.get_submission_class()
        self.submission = submission_class.objects.create(
            page=self.page,
            form_data={
                "email_address": "applicant@example.com",
                "email": "Male",
                "full_name": "Jane Doe",
            },
        )

    def _run(self, apply=False, page_id=None):
        out = io.StringIO()
        kwargs = {"apply": apply}
        if page_id is not None:
            kwargs["page_id"] = page_id
        call_command("repair_form_field_clean_names", stdout=out, **kwargs)
        return out.getvalue()

    def test_dry_run_leaves_everything_untouched(self):
        self._run(apply=False)

        self.gender_field.refresh_from_db()
        self.name_field.refresh_from_db()
        self.submission.refresh_from_db()

        self.assertEqual(self.gender_field.clean_name, "email")
        self.assertEqual(self.name_field.clean_name, "")
        self.assertEqual(
            sorted(self.submission.form_data.keys()),
            ["email", "email_address", "full_name"],
        )

    def test_apply_renames_wrong_nonempty_clean_name_and_moves_submission_data(self):
        self._run(apply=True)

        self.gender_field.refresh_from_db()
        self.assertEqual(self.gender_field.clean_name, "gender")

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.form_data.get("gender"), "Male")
        self.assertNotIn("email", self.submission.form_data)

    def test_apply_fixes_blank_clean_name_without_touching_submission_data(self):
        self._run(apply=True)

        self.name_field.refresh_from_db()
        self.assertEqual(self.name_field.clean_name, "full_name")

        self.submission.refresh_from_db()
        # Data was already correctly stored under "full_name" (the live form's
        # own render-time fallback) - the fix is metadata-only here.
        self.assertEqual(self.submission.form_data.get("full_name"), "Jane Doe")

    def test_apply_leaves_already_correct_field_untouched(self):
        self._run(apply=True)

        self.email_field.refresh_from_db()
        self.assertEqual(self.email_field.clean_name, "email_address")

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.form_data.get("email_address"), "applicant@example.com")

    def test_conflicting_target_clean_name_is_skipped_not_overwritten(self):
        # A second field that would also resolve to "gender" - applying must
        # not silently clobber either field or any submission data.
        conflict_field = self.page.application_form_fields.create(
            label="Gender", field_type="dropdown", required=True, sort_order=3,
        )
        self.page.save()
        conflict_field.refresh_from_db()

        output = self._run(apply=True)

        self.assertIn("collides", output)

        self.gender_field.refresh_from_db()
        self.assertEqual(self.gender_field.clean_name, "email")

        self.submission.refresh_from_db()
        self.assertIn("email", self.submission.form_data)

    def test_page_id_scopes_to_a_single_page(self):
        other_edition = SummerSchoolPageFactory(parent=self.page.get_parent().get_parent())
        other_page = SummerSchoolApplicationPageFactory(parent=other_edition)
        other_gender_field = other_page.application_form_fields.create(
            label="Gender", field_type="dropdown", required=True, sort_order=0,
        )
        other_page.save()
        other_gender_field.refresh_from_db()
        SummerSchoolApplicationFormField.objects.filter(pk=other_gender_field.pk).update(
            clean_name="email"
        )

        self._run(apply=True, page_id=self.page.id)

        self.gender_field.refresh_from_db()
        other_gender_field.refresh_from_db()
        self.assertEqual(self.gender_field.clean_name, "gender")
        self.assertEqual(other_gender_field.clean_name, "email")
