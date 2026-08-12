from django.db import migrations


def backfill_terminal_progress(apps, schema_editor):
    ProductImportRun = apps.get_model('products', 'ProductImportRun')
    ProductImportRun.objects.filter(status='succeeded').update(
        progress_percent=100,
        current_phase='Import completed',
    )
    ProductImportRun.objects.filter(status='failed', current_phase='').update(
        current_phase='Import failed',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0039_productimportrun_progress'),
    ]

    operations = [
        migrations.RunPython(
            backfill_terminal_progress,
            migrations.RunPython.noop,
        ),
    ]
