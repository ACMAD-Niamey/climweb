from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0028_rccdatasetasset_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RCCARC2ImportConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=False)),
                ("interval_hours", models.PositiveSmallIntegerField(default=24)),
                ("selected_stations", models.JSONField(blank=True, default=list)),
                ("discovered_stations", models.JSONField(blank=True, default=list)),
                ("discovered_at", models.DateTimeField(blank=True, null=True)),
                ("discovery_error", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="RCCARC2ImportRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("partial", "Partially succeeded"), ("failed", "Failed")], default="queued", max_length=12)),
                ("trigger", models.CharField(choices=[("manual", "Manual"), ("scheduled", "Scheduled")], max_length=12)),
                ("stations", models.JSONField(default=list)),
                ("results", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("config", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="services.rccarc2importconfig")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
