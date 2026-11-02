from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0073_make_product_intro_title_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="productpage",
            name="show_latest_product_thumbnail_in_introduction",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "When disabled, the configured introduction image is used instead."
                ),
                verbose_name="Show latest product thumbnail in introduction",
            ),
        ),
        migrations.AddField(
            model_name="subnationalproductpage",
            name="show_latest_product_thumbnail_in_introduction",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "When disabled, the configured introduction image is used instead."
                ),
                verbose_name="Show latest product thumbnail in introduction",
            ),
        ),
    ]
