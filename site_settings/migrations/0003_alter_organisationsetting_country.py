# Generated by Django 4.1.9 on 2023-06-14 07:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('site_settings', '0002_integrationsettings_enable_auto_forecast'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisationsetting',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='country_setting', to='site_settings.country', verbose_name='Country'),
        ),
    ]
