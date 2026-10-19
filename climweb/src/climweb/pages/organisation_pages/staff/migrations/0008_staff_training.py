import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import climweb.pages.organisation_pages.staff.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("staff", "0007_staff_existing_accounts"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffTrainingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("organizer", models.CharField(blank=True, max_length=200)),
                ("location", models.CharField(blank=True, max_length=200)),
                ("description", models.TextField(blank=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("report_due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("nominated", "Nominated"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="nominated", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staff_training_assignments_created", to=settings.AUTH_USER_MODEL)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="training_assignments", to="staff.staffmember")),
            ],
            options={"ordering": ["-start_date", "-pk"]},
        ),
        migrations.CreateModel(
            name="StaffTrainingReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=220)),
                ("summary", models.TextField()),
                ("outcomes", models.TextField(blank=True)),
                ("document", models.FileField(blank=True, storage=climweb.pages.organisation_pages.staff.models.staff_report_storage, upload_to=climweb.pages.organisation_pages.staff.models.staff_report_upload_path)),
                ("drive_file_url", models.URLField(blank=True, verbose_name="Google Drive file link")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Awaiting review"), ("published", "Published"), ("changes_requested", "Changes requested")], default="draft", max_length=24)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewer_comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assignment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="report", to="staff.stafftrainingassignment")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_staff_training_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at", "-pk"]},
        ),
    ]
