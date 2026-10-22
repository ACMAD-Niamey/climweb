import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0035_ein15_importer")]

    operations = [
        migrations.AddField(
            model_name="rccarc2importrun",
            name="cancel_requested",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="rcccpcimportrun",
            name="cancel_requested",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="rccarc2importrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"), ("running", "Running"),
                    ("succeeded", "Succeeded"), ("partial", "Partially succeeded"),
                    ("failed", "Failed"), ("cancelled", "Stopped"),
                ],
                default="queued", max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name="rcccpcimportrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"), ("running", "Running"),
                    ("succeeded", "Succeeded"), ("partial", "Partially succeeded"),
                    ("failed", "Failed"), ("cancelled", "Stopped"),
                ],
                default="queued", max_length=12,
            ),
        ),
        migrations.CreateModel(
            name="RCCARC2ImportLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("level", models.CharField(choices=[("info", "Info"), ("success", "Success"), ("warning", "Warning"), ("error", "Error")], max_length=10)),
                ("event", models.CharField(max_length=40)),
                ("station", models.CharField(blank=True, max_length=150)),
                ("message", models.TextField(blank=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="services.rccarc2importrun")),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.CreateModel(
            name="RCCCPCImportLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("level", models.CharField(choices=[("info", "Info"), ("success", "Success"), ("warning", "Warning"), ("error", "Error")], max_length=10)),
                ("event", models.CharField(max_length=40)),
                ("station", models.CharField(blank=True, max_length=150)),
                ("message", models.TextField(blank=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="services.rcccpcimportrun")),
            ],
            options={"ordering": ("id",)},
        ),
    ]
