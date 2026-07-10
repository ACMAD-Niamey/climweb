from django.db import migrations, models
import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
import wagtailiconchooser.blocks


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0039_alter_homemapsettings_zoom_locations'),
        ('wagtailcore', '0094_alter_page_locale'),
    ]

    operations = [
        migrations.AddField(
            model_name='homemapsettings',
            name='multi_hazard_api_base_url',
            field=models.URLField(blank=True, help_text='Base URL for the Multi-Hazard catalog API, for example https://multi-hazard.acmad.org', null=True, verbose_name='Multi-Hazard API base URL'),
        ),
        migrations.AddField(
            model_name='homemapsettings',
            name='multi_hazard_project_slug',
            field=models.CharField(blank=True, default='multi-hazard', max_length=100, verbose_name='Multi-Hazard project slug'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='weather_watch_period',
            field=models.CharField(blank=True, help_text='e.g. 10 – 16 July 2026. Leave blank to derive from the latest item of the source product below', max_length=100, null=True, verbose_name='Outlook period'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='weather_watch_outlook',
            field=wagtail.fields.RichTextField(blank=True, features=['bold', 'ul', 'ol', 'link', 'superscript', 'subscript', 'h2', 'h3', 'h4'], help_text='Short outlook summary shown on the Weather Watch card. Leave blank to derive from the source product below', null=True, verbose_name='Outlook summary'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='weather_watch_indicators',
            field=wagtail.fields.StreamField([('indicator', wagtail.blocks.StructBlock([('label', wagtail.blocks.CharBlock(max_length=30)), ('value', wagtail.blocks.CharBlock(max_length=30))], label='Indicator'))], blank=True, max_num=3, null=True, use_json_field=True, verbose_name='Weather Watch indicators'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='weather_watch_source_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.page', verbose_name='Weather Watch source product'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='featured_products',
            field=wagtail.fields.StreamField([('product', wagtail.blocks.StructBlock([('page', wagtail.blocks.PageChooserBlock(page_type=['products.ProductPage'])), ('custom_title', wagtail.blocks.CharBlock(max_length=60, required=False)), ('custom_blurb', wagtail.blocks.TextBlock(max_length=160, required=False)), ('icon', wagtailiconchooser.blocks.IconChooserBlock(required=False))], label='Product'))], blank=True, max_num=3, null=True, use_json_field=True, verbose_name='Featured Products'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='services_strip',
            field=wagtail.fields.StreamField([('item', wagtail.blocks.StructBlock([('icon', wagtailiconchooser.blocks.IconChooserBlock(default='layer-group')), ('title', wagtail.blocks.CharBlock(max_length=50)), ('description', wagtail.blocks.CharBlock(max_length=120)), ('page', wagtail.blocks.PageChooserBlock(required=False)), ('external_url', wagtail.blocks.URLBlock(required=False))], label='Item'))], blank=True, help_text='Compact link strip below the cards. Leave empty to derive from Service pages.', max_num=5, null=True, use_json_field=True, verbose_name='Services Strip'),
        ),
    ]
