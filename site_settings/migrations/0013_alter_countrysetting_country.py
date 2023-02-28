# Generated by Django 4.1.7 on 2023-02-26 17:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('site_settings', '0012_alter_countrysetting_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='countrysetting',
            name='country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='country_setting', to='site_settings.country'),
        ),
    ]
