from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.contrib.forms.utils import get_form_types
from wagtail.models import Page


class Command(BaseCommand):
    """
    Fixes form fields whose clean_name doesn't match their current label -
    e.g. a field originally created as "Email" (clean_name="email") that was
    later relabeled to "Gender" in the CMS without clean_name following (it's
    only generated once, on creation - see AbstractFormField.save()).

    Unlike a blank clean_name (handled transparently at read time by
    climweb.base.form_utils.effective_clean_name - the live form already
    self-heals that case via Wagtail's own FormBuilder fallback), a
    non-blank-but-wrong clean_name IS the live storage key: the form
    genuinely renders and stores data under it. Fixing it means renaming
    both the field's clean_name AND the matching key in every existing
    submission's form_data, together, so old and new submissions read
    consistently under the field's current, correct name.

    Defaults to a dry run - pass --apply to actually write changes. Skips
    (and reports) any field whose correct clean_name would collide with
    another field's clean_name, or any submission that already has a value
    under the target key, rather than silently overwriting data.
    """

    help = (
        "Renames form fields' clean_name (and the matching key in existing "
        "submissions) to match their current label. Dry run by default - pass "
        "--apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually write the changes. Without this, only reports what would change.",
        )
        parser.add_argument(
            "--page-id", type=int, default=None,
            help="Limit to a single form page's id. Default: every form page sitewide.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        page_id = options["page_id"]

        pages_qs = Page.objects.filter(content_type__in=get_form_types())
        if page_id is not None:
            pages_qs = pages_qs.filter(pk=page_id)

        total_field_renames = 0
        total_submission_updates = 0
        total_conflicts = 0

        with transaction.atomic():
            for page in pages_qs.specific():
                fields = list(page.get_form_fields())
                if not fields:
                    continue

                current_clean_names = {f.clean_name for f in fields if f.clean_name}
                submission_class = page.get_submission_class()
                submissions = None  # lazily fetched only if a field on this page needs it

                page_header_written = False

                for field in fields:
                    old_clean_name = field.clean_name
                    correct_clean_name = field.get_field_clean_name()

                    if old_clean_name == correct_clean_name:
                        continue

                    other_names = current_clean_names - {old_clean_name}
                    if correct_clean_name in other_names:
                        total_conflicts += 1
                        self._log_page_header(page, page_header_written)
                        page_header_written = True
                        self.stdout.write(self.style.WARNING(
                            f"  SKIP field '{field.label}': correct clean_name "
                            f"'{correct_clean_name}' collides with another field on "
                            f"this page - resolve manually."
                        ))
                        continue

                    self._log_page_header(page, page_header_written)
                    page_header_written = True

                    submissions_touched = 0
                    if old_clean_name:
                        # A non-blank clean_name is the field's actual, currently
                        # live storage key - move the data, don't just relabel it.
                        if submissions is None:
                            submissions = list(submission_class.objects.filter(page=page))

                        for submission in submissions:
                            data = submission.form_data
                            if old_clean_name not in data:
                                continue
                            if correct_clean_name in data:
                                total_conflicts += 1
                                self.stdout.write(self.style.WARNING(
                                    f"    SKIP submission {submission.pk}: already has a "
                                    f"value under '{correct_clean_name}' - resolve manually."
                                ))
                                continue

                            data[correct_clean_name] = data.pop(old_clean_name)
                            submissions_touched += 1
                            if apply_changes:
                                submission.save(update_fields=["form_data"])

                        total_submission_updates += submissions_touched

                    self.stdout.write(
                        f"  '{field.label}': clean_name '{old_clean_name or '<blank>'}' "
                        f"-> '{correct_clean_name}'"
                        + (f" ({submissions_touched} submission(s) updated)" if old_clean_name else "")
                    )

                    field.clean_name = correct_clean_name
                    if apply_changes:
                        field.save()
                    total_field_renames += 1
                    current_clean_names.add(correct_clean_name)
                    current_clean_names.discard(old_clean_name)

            if not apply_changes:
                # Roll back - this was a dry run, nothing above should persist.
                transaction.set_rollback(True)

        self.stdout.write("")
        mode = "APPLIED" if apply_changes else "DRY RUN (pass --apply to write these changes)"
        self.stdout.write(self.style.SUCCESS(
            f"{mode}: {total_field_renames} field(s) renamed, "
            f"{total_submission_updates} submission(s) updated, "
            f"{total_conflicts} conflict(s) skipped."
        ))

    def _log_page_header(self, page, already_written):
        if not already_written:
            self.stdout.write(f"Page {page.id} - {page.title}:")
