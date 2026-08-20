from django.db import migrations
import wagtail.blocks
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0040_homepage_redesign_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="hero_featured_products",
            field=wagtail.fields.StreamField(
                [
                    (
                        "product",
                        wagtail.blocks.PageChooserBlock(
                            page_type=["products.ProductPage"]
                        ),
                    )
                ],
                blank=True,
                help_text=(
                    "Choose up to three product families for the rotating hero card. "
                    "Their latest published items are shown in this order. Leave empty "
                    "to use the defaults."
                ),
                max_num=3,
                null=True,
                use_json_field=True,
                verbose_name="Hero Featured Products",
            ),
        ),
    ]
