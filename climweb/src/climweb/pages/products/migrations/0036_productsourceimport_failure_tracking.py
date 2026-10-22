from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0035_productsourceimport'),
    ]

    operations = [
        migrations.AddField(
            model_name='productsourceimport',
            name='attempt_count',
            field=models.PositiveIntegerField(default=1, verbose_name='Attempt Count'),
        ),
        migrations.AddField(
            model_name='productsourceimport',
            name='error_message',
            field=models.TextField(blank=True, verbose_name='Error Message'),
        ),
        migrations.AddField(
            model_name='productsourceimport',
            name='status',
            field=models.CharField(
                choices=[('imported', 'Imported'), ('failed', 'Failed')],
                default='imported',
                max_length=20,
                verbose_name='Status',
            ),
        ),
    ]
