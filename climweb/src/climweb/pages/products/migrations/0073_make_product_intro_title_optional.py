from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0072_product_category_headers_and_partners"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productpage",
            name="introduction_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Introduction section title",
                max_length=100,
                verbose_name="Introduction Title",
            ),
        ),
        migrations.AlterField(
            model_name="subnationalproductpage",
            name="introduction_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Introduction section title",
                max_length=100,
                verbose_name="Introduction Title",
            ),
        ),
    ]
