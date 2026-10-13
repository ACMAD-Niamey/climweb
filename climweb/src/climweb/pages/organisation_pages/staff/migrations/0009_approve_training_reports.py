from django.db import migrations, models


def approve_existing_reports(apps, schema_editor):
    StaffTrainingReport = apps.get_model("staff", "StaffTrainingReport")
    StaffTrainingReport.objects.filter(status="published").update(status="approved")


def restore_published_reports(apps, schema_editor):
    StaffTrainingReport = apps.get_model("staff", "StaffTrainingReport")
    StaffTrainingReport.objects.filter(status="approved").update(status="published")


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0008_staff_training"),
    ]

    operations = [
        migrations.RunPython(approve_existing_reports, restore_published_reports),
        migrations.RenameField(
            model_name="stafftrainingreport",
            old_name="published_at",
            new_name="approved_at",
        ),
        migrations.AlterField(
            model_name="stafftrainingreport",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Awaiting review"),
                    ("approved", "Approved"),
                    ("changes_requested", "Changes requested"),
                ],
                default="draft",
                max_length=24,
            ),
        ),
    ]
