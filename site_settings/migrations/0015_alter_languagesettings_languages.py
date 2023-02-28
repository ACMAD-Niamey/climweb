# Generated by Django 4.0.10 on 2023-02-27 14:43

from django.db import migrations
import wagtail.blocks
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('site_settings', '0014_languagesettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='languagesettings',
            name='languages',
            field=wagtail.fields.StreamField([('languages', wagtail.blocks.StructBlock([('prefix', wagtail.blocks.CharBlock(max_length=5)), ('language', wagtail.blocks.CharBlock(max_length=20)), ('default', wagtail.blocks.BooleanBlock(required=False))]))], blank=True, null=True, use_json_field=False),
        ),
    ]
