import django.db.models.deletion
from django.db import migrations, models


def copy_legacy_lead_update(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    for homepage in HomePage.objects.all().iterator():
        news_id = None
        event_id = None
        for block in homepage.hero_featured_updates or []:
            page_id = getattr(block.value, "pk", None)
            if block.block_type == "news" and news_id is None:
                news_id = page_id
            elif block.block_type == "event" and event_id is None:
                event_id = page_id
        if news_id or event_id:
            HomePage.objects.filter(pk=homepage.pk).update(
                hero_featured_news_id=news_id,
                hero_featured_event_id=event_id,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0015_eventpage_attendance_mode_and_more"),
        ("home", "0046_homepage_hero_carousel_lead"),
        ("news", "0006_alter_newspage_media_gallery"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="hero_featured_event",
            field=models.ForeignKey(
                blank=True,
                help_text="Event page to show after the news slide when Update selection is Manual.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="events.eventpage",
                verbose_name="Event slide",
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="hero_featured_news",
            field=models.ForeignKey(
                blank=True,
                help_text="News page to show first when Update selection is Manual.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="news.newspage",
                verbose_name="News slide",
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="hero_show_el_nino",
            field=models.BooleanField(
                default=True,
                help_text="Include the El Niño programme slide in the carousel.",
                verbose_name="Show El Niño",
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="hero_show_summer_school",
            field=models.BooleanField(
                default=True,
                help_text="Include the Summer School programme slide in the carousel.",
                verbose_name="Show Summer School",
            ),
        ),
        migrations.RunPython(copy_legacy_lead_update, migrations.RunPython.noop),
        migrations.RemoveField(model_name="homepage", name="hero_featured_updates"),
    ]
