from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0042_productimportsourceconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimportschedule',
            name='enabled_override',
            field=models.BooleanField(
                blank=True,
                help_text='Leave empty to use the deployment configuration.',
                null=True,
                verbose_name='Enabled Override',
            ),
        ),
    ]
