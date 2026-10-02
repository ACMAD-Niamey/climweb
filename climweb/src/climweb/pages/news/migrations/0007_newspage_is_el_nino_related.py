from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0006_alter_newspage_media_gallery"),
    ]

    operations = [
        migrations.AddField(
            model_name="newspage",
            name="is_el_nino_related",
            field=models.BooleanField(
                default=False,
                help_text="Show this news item in the news and events section of the El Niño page.",
                verbose_name="El Niño related news",
            ),
        ),
    ]
