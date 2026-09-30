import climweb.pages.home.models
import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("home", "0047_homepage_hero_carousel_controls")]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="hero_carousel_order",
            field=wagtail.fields.StreamField(
                [("news", 0), ("event", 1), ("el_nino", 2), ("summer_school", 3)],
                blank=True,
                block_lookup={
                    0: (
                        "wagtail.blocks.static_block.StaticBlock", (),
                        {"admin_text": "News slide", "label": "News"},
                    ),
                    1: (
                        "wagtail.blocks.static_block.StaticBlock", (),
                        {"admin_text": "Event slide", "label": "Event"},
                    ),
                    2: (
                        "wagtail.blocks.static_block.StaticBlock", (),
                        {"admin_text": "El Niño slide", "label": "El Niño"},
                    ),
                    3: (
                        "wagtail.blocks.static_block.StaticBlock", (),
                        {"admin_text": "Summer School slide", "label": "Summer School"},
                    ),
                },
                default=climweb.pages.home.models.default_hero_carousel_order,
                help_text="In Manual mode, drag these items into the order they should appear. Missing or disabled slides are skipped.",
                verbose_name="Slide order",
            ),
        ),
    ]
