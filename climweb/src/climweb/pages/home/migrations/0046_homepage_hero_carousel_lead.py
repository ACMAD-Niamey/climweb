import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0045_alter_homepage_hero_featured_products")]

    operations = [
        migrations.AlterField(
            model_name="homepage",
            name="hero_featured_updates",
            field=wagtail.fields.StreamField(
                [("news", 0), ("event", 1)], blank=True, null=True, max_num=1,
                block_lookup={
                    0: ("wagtail.blocks.PageChooserBlock", (), {"page_type": ["news.NewsPage"]}),
                    1: ("wagtail.blocks.PageChooserBlock", (), {"page_type": ["events.EventPage"]}),
                },
                help_text="In Manual mode, choose one news or event page for the first slide. Leave empty to show only the El Niño, HeatEWS and Summer School slides.",
                verbose_name="Lead update",
            ),
        ),
        migrations.AlterField(
            model_name="homepage",
            name="hero_updates_mode",
            field=models.CharField(
                choices=[("automatic", "Automatic"), ("manual", "Manual")],
                default="automatic",
                help_text="Automatic uses the newest news item as the lead slide. Only public, published pages from this homepage are included.",
                max_length=10,
                verbose_name="Update selection",
            ),
        ),
    ]
