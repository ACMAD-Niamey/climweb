# Generated by Django 3.2.20 on 2023-09-01 10:28

from django.db import migrations
import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks


class Migration(migrations.Migration):

    dependencies = [
        ('about', '0004_aboutpage_accordion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aboutpage',
            name='feature_block',
            field=wagtail.fields.StreamField([('feature_item', wagtail.blocks.StructBlock([('figure_type', wagtail.blocks.ChoiceBlock(choices=[('image', 'Image'), ('chart', 'Chart'), ('video', 'Video'), ('imageofchange', 'Image of Change')])), ('image', wagtail.images.blocks.ImageChooserBlock(required=False)), ('chart_config_url', wagtail.blocks.URLBlock(help_text='A URL that returns Highcharts.js configuration, including the data', required=False)), ('title', wagtail.blocks.CharBlock()), ('text', wagtail.blocks.RichTextBlock(features=['bold', 'ul', 'ol', 'link', 'superscript', 'subscript'], label='Description')), ('action_link_text', wagtail.blocks.CharBlock(max_length=15, required=False)), ('action_link', wagtail.blocks.PageChooserBlock(label='Action Link Internal', required=False)), ('action_link_external', wagtail.blocks.URLBlock(help_text='An external link to a detailed resource on the internet.If provided, the internal link will be ignored', max_length=400, required=False))]))], blank=True, null=True, use_json_field=True, verbose_name='Feature Block'),
        ),
    ]
