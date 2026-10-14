import django.db.models.deletion
from django.db import migrations, models

import climweb.pages.organisation_pages.staff.models


def move_existing_documents(apps, schema_editor):
    Report = apps.get_model("staff", "StaffTrainingReport")
    Document = apps.get_model("staff", "StaffTrainingReportDocument")
    for report in Report.objects.exclude(document="").iterator():
        name = report.document.name
        Document.objects.create(
            report_id=report.pk,
            file=name,
            original_name=name.rsplit("/", 1)[-1],
        )


def restore_first_document(apps, schema_editor):
    Report = apps.get_model("staff", "StaffTrainingReport")
    Document = apps.get_model("staff", "StaffTrainingReportDocument")
    for report in Report.objects.iterator():
        document = Document.objects.filter(report_id=report.pk).order_by("uploaded_at", "pk").first()
        if document:
            report.document = document.file.name
            report.save(update_fields=["document"])


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0011_activity_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffTrainingReportDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "file",
                    models.FileField(
                        storage=climweb.pages.organisation_pages.staff.models.staff_report_storage,
                        upload_to=climweb.pages.organisation_pages.staff.models.staff_report_upload_path,
                    ),
                ),
                ("original_name", models.CharField(max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="staff.stafftrainingreport",
                    ),
                ),
            ],
            options={"ordering": ["uploaded_at", "pk"]},
        ),
        migrations.RunPython(move_existing_documents, restore_first_document),
        migrations.RemoveField(
            model_name="stafftrainingreport",
            name="document",
        ),
    ]
