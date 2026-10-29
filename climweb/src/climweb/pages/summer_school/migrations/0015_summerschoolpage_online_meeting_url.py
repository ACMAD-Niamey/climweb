from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("summer_school", "0014_alter_summerschoolindexpage_editions_per_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="summerschoolpage",
            name="online_meeting_url",
            field=models.URLField(
                blank=True,
                help_text=(
                    "When provided, the featured Summer School buttons link to the live online event. "
                    "Clear this field when online participation is no longer available."
                ),
                verbose_name="Online meeting URL",
            ),
        ),
    ]
