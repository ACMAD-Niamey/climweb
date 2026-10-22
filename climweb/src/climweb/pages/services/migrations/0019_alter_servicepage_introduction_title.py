from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0018_alter_servicepage_service_sectors"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepage",
            name="introduction_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional introduction section title",
                max_length=100,
                verbose_name="Introduction Title",
            ),
        ),
    ]
