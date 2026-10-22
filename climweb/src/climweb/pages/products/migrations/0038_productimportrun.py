from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0037_productsourceimport_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductImportRun',
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
                ('product_family', models.CharField(max_length=80, verbose_name='Product Family')),
                (
                    'mode',
                    models.CharField(
                        choices=[('preview', 'Preview'), ('import', 'Import')],
                        max_length=20,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('queued', 'Queued'),
                            ('running', 'Running'),
                            ('succeeded', 'Succeeded'),
                            ('failed', 'Failed'),
                        ],
                        default='queued',
                        max_length=20,
                    ),
                ),
                ('from_date', models.DateField(verbose_name='From Date')),
                ('to_date', models.DateField(verbose_name='To Date')),
                ('limit', models.PositiveIntegerField(default=100)),
                ('refresh_existing', models.BooleanField(default=False)),
                ('retry_failures', models.BooleanField(default=False)),
                ('task_id', models.CharField(blank=True, max_length=255)),
                ('output', models.TextField(blank=True)),
                ('error_message', models.TextField(blank=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                (
                    'requested_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='product_import_runs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Product Import Run',
                'verbose_name_plural': 'Product Import Runs',
                'ordering': ['-requested_at'],
            },
        ),
    ]
