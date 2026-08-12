from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0045_alter_productimportsourceconfig_source_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimportrun",
            name="cancel_requested",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="productimportrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("cancelling", "Stopping"),
                    ("cancelled", "Stopped"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                ],
                default="queued",
                max_length=20,
            ),
        ),
    ]
