from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0038_productimportrun'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimportrun',
            name='current_phase',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='productimportrun',
            name='failed_items',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productimportrun',
            name='imported_items',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productimportrun',
            name='processed_items',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productimportrun',
            name='progress_percent',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productimportrun',
            name='skipped_items',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productimportrun',
            name='total_items',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
