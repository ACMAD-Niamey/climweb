from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0010_staff_notification_delivery"),
    ]

    operations = [
        migrations.AddField(
            model_name="stafftrainingassignment",
            name="activity_type",
            field=models.CharField(
                choices=[
                    ("training", "Training"),
                    ("workshop", "Workshop"),
                    ("event", "Conference or event"),
                    ("meeting", "Meeting"),
                    ("other", "Other"),
                ],
                default="training",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="staffnotificationdelivery",
            name="event",
            field=models.CharField(
                choices=[
                    ("training_assigned", "Activity assigned"),
                    ("report_submitted", "Report submitted"),
                    ("report_approved", "Report approved"),
                    ("report_changes_requested", "Report changes requested"),
                    ("report_due_7_days", "Report due in 7 days"),
                    ("report_due_3_days", "Report due in 3 days"),
                    ("report_due_1_day", "Report due in 1 day"),
                    ("report_overdue", "Report overdue"),
                ],
                max_length=40,
            ),
        ),
    ]
