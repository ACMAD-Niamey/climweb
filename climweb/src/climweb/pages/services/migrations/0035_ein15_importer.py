import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0034_rccseasonalmapasset_rccseasonalmapimportconfig_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RCCEIN15ImportConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("singleton_key", models.CharField(default="ein15", editable=False, max_length=20, unique=True)),
                ("catalogue_url", models.URLField(default="http://sgbd.acmad.org:8080/thredds/catalog/ein15output/catalog.xml", max_length=700)),
                ("enabled", models.BooleanField(default=False)),
                ("interval_hours", models.PositiveSmallIntegerField(default=168)),
                ("discovered_files", models.JSONField(blank=True, default=list)),
                ("selected_files", models.JSONField(blank=True, default=list)),
                ("discovered_at", models.DateTimeField(blank=True, null=True)),
                ("discovery_error", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="RCCEIN15Asset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(max_length=100, unique=True)),
                ("source_url", models.URLField(max_length=700)),
                ("object_name", models.CharField(max_length=500)),
                ("checksum_sha256", models.CharField(max_length=64)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("source_last_modified", models.CharField(blank=True, max_length=100)),
                ("synced_at", models.DateTimeField()),
            ],
            options={"ordering": ("filename",)},
        ),
        migrations.CreateModel(
            name="RCCEIN15ImportRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("partial", "Partially succeeded"), ("failed", "Failed")], default="queued", max_length=12)),
                ("trigger", models.CharField(choices=[("manual", "Manual"), ("scheduled", "Scheduled")], max_length=12)),
                ("files", models.JSONField(default=list)),
                ("catalogue_url", models.URLField(max_length=700)),
                ("results", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("config", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="services.rccein15importconfig")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
