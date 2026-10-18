from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0053_merge_20260922_0830"),
        ("products", "0070_productindexpage_featured_product_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productpage",
            name="gis_application",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional GIS application shown in place of the introduction image.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="base.application",
                verbose_name="GIS application",
            ),
        ),
        migrations.AddField(
            model_name="subnationalproductpage",
            name="gis_application",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional GIS application shown in place of the introduction image.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="base.application",
                verbose_name="GIS application",
            ),
        ),
    ]
