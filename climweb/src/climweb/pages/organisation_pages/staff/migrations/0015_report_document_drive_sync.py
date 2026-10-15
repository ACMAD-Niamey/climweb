from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0014_staff_drive"),
    ]

    operations = [
        migrations.AddField(
            model_name="stafftrainingreportdocument",
            name="drive_file_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="stafftrainingreportdocument",
            name="drive_sync_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="stafftrainingreportdocument",
            name="drive_sync_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("synced", "Synced"),
                    ("failed", "Failed"),
                    ("disabled", "Drive disabled"),
                ],
                default="pending",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="stafftrainingreportdocument",
            name="drive_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
