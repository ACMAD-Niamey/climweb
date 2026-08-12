from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0041_productimportschedule'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductImportSourceConfig',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'product_family',
                    models.CharField(
                        max_length=80,
                        unique=True,
                        verbose_name='Product Family',
                    ),
                ),
                (
                    'source_type',
                    models.CharField(
                        choices=[
                            ('html_archive', 'HTML archive or directory listing'),
                        ],
                        default='html_archive',
                        max_length=40,
                        verbose_name='Source Type',
                    ),
                ),
                (
                    'source_url',
                    models.URLField(max_length=1000, verbose_name='Source URL'),
                ),
                (
                    'source_system',
                    models.CharField(max_length=255, verbose_name='Source Name'),
                ),
                ('allowed_extensions', models.JSONField(default=list)),
                (
                    'filename_pattern',
                    models.TextField(verbose_name='Filename Pattern'),
                ),
                (
                    'date_format',
                    models.CharField(
                        default='%Y%m%d',
                        max_length=80,
                        verbose_name='Date Format',
                    ),
                ),
                (
                    'history_url_pattern',
                    models.TextField(
                        blank=True,
                        verbose_name='Historical Archive Pattern',
                    ),
                ),
                ('request_headers', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='product_import_source_configs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Product Import Source Configuration',
                'verbose_name_plural': 'Product Import Source Configurations',
                'ordering': ['product_family'],
            },
        ),
    ]
