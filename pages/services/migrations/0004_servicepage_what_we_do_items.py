# Generated by Django 4.1.9 on 2023-07-10 12:54

from django.db import migrations
import wagtail.blocks
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_alter_serviceindexpage_listing_heading'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicepage',
            name='what_we_do_items',
            field=wagtail.fields.StreamField([('what_we_do', wagtail.blocks.StructBlock([('icon', wagtail.blocks.CharBlock(required=False)), ('title', wagtail.blocks.CharBlock(max_length=60, required=False)), ('description', wagtail.blocks.CharBlock())]))], blank=True, null=True, use_json_field=True),
        ),
    ]
