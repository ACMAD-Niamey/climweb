# Generated by Django 4.1.7 on 2023-02-28 20:53

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import wagtail.blocks
import wagtail.documents.blocks
import wagtail.fields
import wagtail.images.blocks


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0005_remove_application_show_in_geoportal'),
        ('wagtailcore', '0083_workflowcontenttype'),
        ('wagtailimages', '0025_alter_image_file_alter_rendition_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='TendersIndexPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('banner_title', models.CharField(max_length=255)),
                ('banner_subtitle', models.CharField(blank=True, max_length=255, null=True)),
                ('call_to_action_button_text', models.CharField(blank=True, max_length=100, null=True)),
                ('introduction_title', models.CharField(help_text='Introduction section title', max_length=100)),
                ('introduction_text', wagtail.fields.RichTextField(help_text='A description of tenders at your organisation')),
                ('introduction_button_text', models.TextField(blank=True, max_length=20, null=True)),
                ('no_tenders_header_text', models.TextField(blank=True, help_text='Text to appear when there are no tenders', null=True)),
                ('no_tenders_description_text', models.TextField(blank=True, help_text='Additional text to appear when there are no tenders,below the no tenders header text', null=True)),
                ('items_per_page', models.PositiveIntegerField(default=6, help_text='How many items should be visible on the landing page filter section ?', validators=[django.core.validators.MinValueValidator(6), django.core.validators.MaxValueValidator(20)])),
                ('banner_image', models.ForeignKey(blank=True, help_text='A high quality image related to Tenders', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Banner Image')),
                ('call_to_action_related_page', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page')),
                ('introduction_button_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page')),
                ('introduction_image', models.ForeignKey(blank=True, help_text='A high quality image related to tenders at your organisation', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image', verbose_name='Introduction Image')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='TenderDetailPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('posting_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date of Posting')),
                ('ref_no', models.CharField(blank=True, help_text='Any Reference number if available', max_length=100, null=True, verbose_name='Reference Number')),
                ('deadline', models.DateTimeField(verbose_name='Submission Deadline')),
                ('description', wagtail.fields.RichTextField(blank=True, null=True)),
                ('additional_documents', wagtail.fields.StreamField([('additional_documents', wagtail.blocks.StructBlock([('type', wagtail.blocks.ChoiceBlock(choices=[('document', 'Document/File'), ('image', 'Image')])), ('title', wagtail.blocks.CharBlock(max_length=255)), ('document', wagtail.documents.blocks.DocumentChooserBlock(help_text='Select document or file', required=False, verbose_name='Document/File')), ('image', wagtail.images.blocks.ImageChooserBlock(help_text='Select/upload image', required=False))]))], blank=True, null=True, use_json_field=True)),
                ('tender_document', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.customdocumentmodel', verbose_name='Downloadable tender description document')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]
