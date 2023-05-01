# Generated by Django 4.1.7 on 2023-03-01 22:51

import integrations.webicons.blocks
from django.db import migrations
import wagtail.blocks
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0008_remove_serviceindexpage_what_we_do_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceindexpage',
            name='what_we_do_items',
            field=wagtail.fields.StreamField([('what_we_do', wagtail.blocks.StructBlock([('icon', integrations.webicons.blocks.WebIconChooserBlock()), ('title', wagtail.blocks.CharBlock(max_length=60, required=False)), ('description', wagtail.blocks.CharBlock())]))], blank=True, null=True, use_json_field=True),
        ),
    ]
