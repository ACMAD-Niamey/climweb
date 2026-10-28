import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0004_alter_partnerspage_introduction_button_text"),
        ("products", "0071_product_gis_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="productpage",
            name="header_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Leave blank to use the main Products page banner image.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Header image",
            ),
        ),
        migrations.AddField(
            model_name="productpage",
            name="header_subtitle",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Header subtitle",
            ),
        ),
        migrations.AddField(
            model_name="productpage",
            name="header_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Leave blank to use the page title.",
                max_length=255,
                verbose_name="Header title",
            ),
        ),
        migrations.AddField(
            model_name="productpage",
            name="product_partners",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                help_text="Selected partner logos appear below the introduction text.",
                related_name="+",
                to="partners.partner",
                verbose_name="Introduction partners",
            ),
        ),
        migrations.AddField(
            model_name="subnationalproductpage",
            name="header_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Leave blank to use the main Products page banner image.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Header image",
            ),
        ),
        migrations.AddField(
            model_name="subnationalproductpage",
            name="header_subtitle",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Header subtitle",
            ),
        ),
        migrations.AddField(
            model_name="subnationalproductpage",
            name="header_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Leave blank to use the page title.",
                max_length=255,
                verbose_name="Header title",
            ),
        ),
        migrations.AddField(
            model_name="subnationalproductpage",
            name="product_partners",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                help_text="Selected partner logos appear below the introduction text.",
                related_name="+",
                to="partners.partner",
                verbose_name="Introduction partners",
            ),
        ),
    ]
