# Generated by Django 4.1.9 on 2023-05-16 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site_settings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='integrationsettings',
            name='auto_forecast',
            field=models.BooleanField(default=False, verbose_name='Enable automated forecasts'),
        ),
    ]
