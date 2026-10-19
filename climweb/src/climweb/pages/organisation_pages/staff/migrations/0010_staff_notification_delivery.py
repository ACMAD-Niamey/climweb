from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0009_approve_training_reports"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffNotificationDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(choices=[("training_assigned", "Training assigned"), ("report_submitted", "Report submitted"), ("report_approved", "Report approved"), ("report_changes_requested", "Report changes requested"), ("report_due_7_days", "Report due in 7 days"), ("report_due_3_days", "Report due in 3 days"), ("report_due_1_day", "Report due in 1 day"), ("report_overdue", "Report overdue")], max_length=40)),
                ("recipient", models.EmailField(max_length=254)),
                ("dedupe_key", models.CharField(max_length=64, unique=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")], default="pending", max_length=12)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_deliveries", to="staff.stafftrainingassignment")),
                ("report", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notification_deliveries", to="staff.stafftrainingreport")),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="staffnotificationdelivery",
            index=models.Index(fields=["status", "created_at"], name="staff_notif_status_created"),
        ),
    ]
