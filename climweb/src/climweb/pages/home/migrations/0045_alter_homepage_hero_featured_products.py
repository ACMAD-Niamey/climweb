import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("home", "0044_homepage_hero_featured_updates_and_more")]

    operations = [
        migrations.AlterField(
            model_name="homepage",
            name="hero_featured_products",
            field=wagtail.fields.StreamField(
                [("product", 0)], blank=True, null=True,
                block_lookup={
                    0: (
                        "wagtail.blocks.PageChooserBlock", (),
                        {"page_type": ["products.ProductPage"]},
                    ),
                },
                help_text="Choose up to three product families for the rotating utility bar. Their latest published items are shown in this order. Leave empty to use the defaults.",
                verbose_name="Utility Navbar Products",
            ),
        ),
    ]
