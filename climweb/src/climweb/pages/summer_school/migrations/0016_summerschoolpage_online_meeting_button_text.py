from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("summer_school", "0015_summerschoolpage_online_meeting_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="summerschoolpage",
            name="online_meeting_button_text",
            field=models.CharField(
                default="Join Summer School Online",
                max_length=60,
                verbose_name="Online meeting button text",
            ),
        ),
    ]
