# Generated by Django 4.0.10 on 2023-02-27 11:27

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactpage',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(help_text='Location of organisation', null=True, srid=4326),
        ),
    ]
