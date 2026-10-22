import csv
import io
import os
import zipfile

import openpyxl

from climweb.base.form_utils import effective_clean_name
from climweb.base.models import FormFileSubmission


def _build_rows(page):
    """Column headings + one row per submission, resolving image/document
    fields to (in-zip file path, original file name) instead of the public
    URL CustomSubmissionsListView.get_file_submission_url uses - see
    climweb.base.forms - since this export is meant to be self-contained and
    doesn't assume the recipient can reach the live site's /media/ files.
    """
    field_types = {
        effective_clean_name(field): field.field_type for field in page.get_form_fields()
    }
    data_fields = page.get_data_fields()
    # str() the labels - "Submission date" comes through as a lazy
    # translation proxy (see FormCleanNameFallbackMixin.get_data_fields),
    # which openpyxl's Cell.value setter rejects outright.
    headings = [str(label) for _name, label in data_fields]

    submissions = page.get_submissions()
    file_pks = {
        value for submission in submissions for name, value in submission.get_data().items()
        if field_types.get(name) in ('image', 'document') and value
    }
    file_submissions_by_pk = FormFileSubmission.objects.in_bulk(file_pks)

    rows = []
    files_to_zip = []  # (arcname, absolute disk path)
    used_arcnames = set()

    for submission in submissions:
        data = submission.get_data()
        row = []
        for name, _label in data_fields:
            value = data.get(name)
            field_type = field_types.get(name)

            if field_type in ('image', 'document') and value:
                file_submission = file_submissions_by_pk.get(value)
                if file_submission and file_submission.file and os.path.exists(file_submission.file.path):
                    original_name = os.path.basename(file_submission.file.name)
                    arcname = f"files/submission_{submission.pk}_{name}_{original_name}"
                    # in_bulk() can't collide on pk, but two fields on the
                    # same submission could coincidentally share a generated
                    # name if the same file were reused - guard anyway so a
                    # write never silently overwrites an earlier one.
                    suffix = 1
                    base_arcname = arcname
                    while arcname in used_arcnames:
                        root, ext = os.path.splitext(base_arcname)
                        arcname = f"{root}_{suffix}{ext}"
                        suffix += 1
                    used_arcnames.add(arcname)
                    files_to_zip.append((arcname, file_submission.file.path))
                    row.append(arcname)
                else:
                    row.append('')
            elif isinstance(value, list):
                row.append(', '.join(str(v) for v in value))
            else:
                row.append('' if value is None else value)

        rows.append(row)

    return headings, rows, files_to_zip, submissions.count()


def _build_xlsx(headings, rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Submissions'
    sheet.append(headings)
    for row in rows:
        sheet.append([str(v) if not isinstance(v, (int, float, type(None))) else v for v in row])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _build_csv(headings, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headings)
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def build_submission_export_zip(page, destination_path):
    """Writes a zip containing submissions.xlsx + submissions.csv (both
    listing the in-zip path for any image/document field, under files/) plus
    the actual uploaded files, to destination_path. Returns the submission
    count. Files are written to the zip straight from disk (FileSystemStorage
    gives a real path) rather than read fully into memory first, since a
    resume/support-letter pair per applicant adds up across a large cohort.
    """
    headings, rows, files_to_zip, submission_count = _build_rows(page)

    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with zipfile.ZipFile(destination_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('submissions.xlsx', _build_xlsx(headings, rows))
        zf.writestr('submissions.csv', _build_csv(headings, rows))
        for arcname, disk_path in files_to_zip:
            zf.write(disk_path, arcname=arcname)

    return submission_count
