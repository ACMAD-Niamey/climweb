from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0044_productindexpage_banner_image_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productimportsourceconfig",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("html_archive", "HTML archive or directory listing"),
                    ("thredds_catalog", "THREDDS XML catalogue"),
                    ("wordpress_api", "WordPress media API"),
                ],
                default="html_archive",
                max_length=40,
                verbose_name="Source Type",
            ),
        ),
    ]
