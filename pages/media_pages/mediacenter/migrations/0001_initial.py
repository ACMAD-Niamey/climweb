# Generated by Django 4.2.2 on 2023-06-14 19:24

from django.db import migrations, models
import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks
import wagtailmetadata.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('videos', '0001_initial'),
        ('wagtailimages', '0025_alter_image_file_alter_rendition_file'),
        ('wagtailcore', '0083_workflowcontenttype'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaIndexPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('banner_title', models.CharField(max_length=255, verbose_name='Banner Title')),
                ('banner_subtitle', models.CharField(blank=True, max_length=255, null=True, verbose_name='Banner Subtitle')),
                ('call_to_action_button_text', models.CharField(blank=True, max_length=100, null=True, verbose_name='Call to action button text')),
                ('introduction_title', models.CharField(help_text='Introduction section title', max_length=100, verbose_name='Introduction Title')),
                ('introduction_text', wagtail.fields.RichTextField(help_text='Introduction section description', verbose_name='Introduction text')),
                ('introduction_button_text', models.TextField(blank=True, max_length=20, null=True, verbose_name='Introduction button text')),
                ('feature_block_items', wagtail.fields.StreamField([('feature_item', wagtail.blocks.StructBlock([('figure_type', wagtail.blocks.ChoiceBlock(choices=[('image', 'Image'), ('chart', 'Chart'), ('video', 'Video'), ('imageofchange', 'Image of Change')])), ('image', wagtail.images.blocks.ImageChooserBlock(required=False)), ('chart_config_url', wagtail.blocks.URLBlock(help_text='A URL that returns Highcharts.js configuration, including the data', required=False)), ('title', wagtail.blocks.CharBlock()), ('text', wagtail.blocks.TextBlock(label='Description')), ('action_link_text', wagtail.blocks.CharBlock(max_length=15, required=False)), ('action_link', wagtail.blocks.PageChooserBlock(label='Action Link Internal', required=False)), ('action_link_external', wagtail.blocks.URLBlock(help_text='An external link to a detailed resource on the internet.If provided, the internal link will be ignored', max_length=400, required=False))]))], blank=True, null=True, use_json_field=True, verbose_name='Items')),
                ('banner_image', models.ForeignKey(blank=True, help_text='A high quality banner image', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Banner Image')),
                ('call_to_action_related_page', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page', verbose_name='Call to action related page')),
                ('introduction_button_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page', verbose_name='Introduction button link')),
                ('introduction_image', models.ForeignKey(blank=True, help_text='A high quality image', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Introduction Image')),
                ('search_image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Search image')),
                ('youtube_playlist', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='videos.youtubeplaylist', verbose_name='Youtube playlist')),
            ],
            options={
                'verbose_name': 'Media Page',
            },
            bases=(wagtailmetadata.models.WagtailImageMetadataMixin, 'wagtailcore.page', models.Model),
        ),
    ]
