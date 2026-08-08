from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0044_submissionemaillog'),
        ('products', '0034_productpage_is_featured_on_homepage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductSourceImport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_url', models.URLField(max_length=1000, unique=True, verbose_name='Source URL')),
                ('source_system', models.CharField(max_length=255, verbose_name='Source System')),
                ('source_published_date', models.DateField(verbose_name='Source Published Date')),
                ('checksum_sha256', models.CharField(max_length=64, verbose_name='SHA-256 Checksum')),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_source_imports', to='base.customdocumentmodel', verbose_name='Document')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_imports', to='base.product', verbose_name='Product')),
                ('product_item_page', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_imports', to='products.productitempage', verbose_name='Product Item Page')),
            ],
            options={
                'verbose_name': 'Product Source Import',
                'verbose_name_plural': 'Product Source Imports',
                'ordering': ['-source_published_date', '-imported_at'],
            },
        ),
    ]
