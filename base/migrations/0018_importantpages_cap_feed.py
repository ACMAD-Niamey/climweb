# Generated by Django 4.2.3 on 2023-08-06 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0017_alter_importantpages_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='importantpages',
            name='cap_feed',
            field=models.URLField(blank=True, null=True, verbose_name='CAP Alerts RSS Feed'),
        ),
    ]
