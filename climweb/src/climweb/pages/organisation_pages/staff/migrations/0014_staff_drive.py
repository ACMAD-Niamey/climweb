import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("staff", "0013_activity_nomination_removed_notification"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffDriveFolder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("folder_id", models.CharField(max_length=255, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("member", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="drive_folder", to="staff.staffmember")),
            ],
        ),
        migrations.CreateModel(
            name="StaffDriveAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("staff_folder_created", "Staff folder created"), ("folder_created", "Folder created"), ("file_uploaded", "File uploaded"), ("file_downloaded", "File downloaded"), ("item_renamed", "Item renamed"), ("item_moved", "Item moved"), ("item_trashed", "Item moved to trash")], max_length=32)),
                ("file_id", models.CharField(max_length=255)),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staff_drive_actions", to=settings.AUTH_USER_MODEL)),
                ("member", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="drive_actions", to="staff.staffmember")),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AddIndex(
            model_name="staffdriveaudit",
            index=models.Index(fields=["member", "created_at"], name="staff_drive_member_created"),
        ),
    ]
