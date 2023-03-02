# Generated by Django 4.1.7 on 2023-02-28 21:14

from django.db import migrations, models
import django.db.models.deletion
import wagtail.blocks
import wagtail.documents.blocks
import wagtail.fields
import wagtail.images.blocks


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtailimages', '0025_alter_image_file_alter_rendition_file'),
        ('wagtailcore', '0083_workflowcontenttype'),
        ('webicons', '0003_alter_webicon_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnersIndexPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('banner_title', models.CharField(max_length=255)),
                ('banner_subtitle', models.CharField(blank=True, max_length=255, null=True)),
                ('call_to_action_button_text', models.CharField(blank=True, max_length=100, null=True)),
                ('introduction_title', models.CharField(help_text='Introduction section title', max_length=100)),
                ('introduction_text', wagtail.fields.RichTextField(help_text='A summary of your organisation relations with partners')),
                ('introduction_button_text', models.TextField(blank=True, max_length=20, null=True)),
                ('partners_cta_title', models.CharField(help_text='Partners call to action section title', max_length=100, verbose_name='Partners Call to Action title')),
                ('partners_cta_text', wagtail.fields.RichTextField(help_text='Call to action description text', verbose_name='Partners call to action text')),
                ('partners_cta_button_text', models.TextField(blank=True, max_length=20, null=True, verbose_name='Partners call to action button text')),
                ('banner_image', models.ForeignKey(blank=True, help_text='A high quality image related to Partners', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Banner Image')),
                ('call_to_action_related_page', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page')),
                ('introduction_button_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page')),
                ('introduction_image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='webicons.webicon', verbose_name='Partners SVG Illustration')),
                ('partners_cta_button_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page', verbose_name='Partners call to action page')),
                ('partners_cta_image', models.ForeignKey(blank=True, help_text='A high quality image related to the Partners call to action message', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Partners call to action Image')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('link', models.URLField(blank=True, help_text='Link to the partners website', max_length=500, null=True, verbose_name="Link to partner's website")),
                ('order', models.PositiveIntegerField(default=0)),
                ('visible_on_homepage', models.BooleanField(default=False)),
                ('is_main', models.BooleanField(default=False)),
                ('logo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='wagtailimages.image')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='AboutPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('introduction_title', models.CharField(help_text='Introduction section title', max_length=100)),
                ('introduction_text', wagtail.fields.RichTextField(help_text='A short summary of your organisation as an organisation')),
                ('introduction_button_text', models.TextField(blank=True, max_length=20, null=True)),
                ('timeline_heading', models.CharField(blank=True, max_length=255, null=True)),
                ('timeline', wagtail.fields.StreamField([('nmhs_timeline', wagtail.blocks.StructBlock([('year', wagtail.blocks.CharBlock(max_length=5)), ('milestones', wagtail.blocks.ListBlock(wagtail.blocks.StructBlock([('period', wagtail.blocks.CharBlock(help_text='This can be the month of the year or the exact date. Leave blank if not known', max_length=50, required=False)), ('description', wagtail.blocks.TextBlock(help_text='Describe the milestone', required=False))])))]))], blank=True, null=True, use_json_field=True, verbose_name='Timeline items')),
                ('feature_block', wagtail.fields.StreamField([('feature_item', wagtail.blocks.StructBlock([('figure_type', wagtail.blocks.ChoiceBlock(choices=[('image', 'Image'), ('chart', 'Chart'), ('video', 'Video'), ('imageofchange', 'Image of Change')])), ('image', wagtail.images.blocks.ImageChooserBlock(required=False)), ('chart_config_url', wagtail.blocks.URLBlock(help_text='A URL that returns Highcharts.js configuration, including the data', required=False)), ('title', wagtail.blocks.CharBlock()), ('text', wagtail.blocks.TextBlock(label='Description')), ('action_link_text', wagtail.blocks.CharBlock(max_length=15, required=False)), ('action_link', wagtail.blocks.PageChooserBlock(label='Action Link Internal', required=False)), ('action_link_external', wagtail.blocks.URLBlock(help_text='An external link to a detailed resource on the internet.If provided, the internal link will be ignored', max_length=400, required=False))]))], blank=True, null=True, use_json_field=True)),
                ('additional_materials', wagtail.fields.StreamField([('material', wagtail.blocks.StructBlock([('category', wagtail.blocks.CharBlock(max_length=255)), ('materials', wagtail.blocks.ListBlock(wagtail.blocks.StructBlock([('type', wagtail.blocks.ChoiceBlock(choices=[('document', 'Document/File'), ('image', 'Image')])), ('title', wagtail.blocks.CharBlock(max_length=255)), ('document', wagtail.documents.blocks.DocumentChooserBlock(help_text='Select document or file', required=False, verbose_name='Document/File')), ('image', wagtail.images.blocks.ImageChooserBlock(help_text='Select/upload image', required=False))])))]))], blank=True, null=True, use_json_field=True)),
                ('bottom_call_to_action_heading', models.CharField(blank=True, max_length=100, null=True)),
                ('bottom_call_to_action_description', models.TextField(blank=True, null=True)),
                ('bottom_call_to_action_button_text', models.CharField(blank=True, max_length=20, null=True)),
                ('bottom_call_to_action_button_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page')),
                ('introduction_button_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page')),
                ('introduction_image', models.ForeignKey(blank=True, help_text='A high quality image related to your organisation as an organisation', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Introduction Image')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]
