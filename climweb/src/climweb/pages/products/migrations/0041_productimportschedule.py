from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0040_backfill_productimportrun_progress'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductImportSchedule',
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
                    'interval_hours',
                    models.PositiveIntegerField(
                        default=24,
                        validators=[MinValueValidator(1), MaxValueValidator(720)],
                        verbose_name='Interval Hours',
                    ),
                ),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='product_import_schedules',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Product Import Schedule',
                'verbose_name_plural': 'Product Import Schedules',
                'ordering': ['product_family'],
            },
        ),
    ]
