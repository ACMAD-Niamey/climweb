import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0043_regionalclimatecentre")]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="hero_featured_updates",
            field=wagtail.fields.StreamField(
                [("news", 0), ("event", 1)], blank=True, null=True,
                block_lookup={
                    0: ("wagtail.blocks.PageChooserBlock", (), {"page_type": ["news.NewsPage"]}),
                    1: ("wagtail.blocks.PageChooserBlock", (), {"page_type": ["events.EventPage"]}),
                },
                help_text="In Manual mode, choose and order up to three news or event pages. An empty selection hides the hero card. Edit titles, images and text on the original pages.",
                verbose_name="Selected updates",
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="hero_updates_mode",
            field=models.CharField(
                choices=[("automatic", "Automatic"), ("manual", "Manual")], default="automatic",
                help_text="Automatic shows the nearest upcoming/ongoing event, then the newest news. Only public, published pages from this homepage are included.",
                max_length=10, verbose_name="Update selection",
            ),
        ),
    ]
