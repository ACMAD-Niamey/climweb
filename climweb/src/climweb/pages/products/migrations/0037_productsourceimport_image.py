from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0036_productsourceimport_failure_tracking'),
        ('wagtailimages', '0026_delete_uploadedimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='productsourceimport',
            name='image',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='product_source_imports',
                to='wagtailimages.image',
                verbose_name='Image',
            ),
        ),
    ]
