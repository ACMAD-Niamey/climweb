from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0015_eventpage_attendance_mode_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventpage",
            name="is_el_nino_related",
            field=models.BooleanField(
                default=False,
                help_text="Show this event in the related events section of the El Niño page.",
                verbose_name="El Niño related event",
            ),
        ),
    ]
