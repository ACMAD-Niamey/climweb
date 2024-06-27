# Generated by Django 4.2.7 on 2024-06-14 10:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0089_log_entry_data_json_null_to_object'),
        ('cap', '0019_alter_capalertpage_options_alter_capalertpage_guid_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OtherCAPSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active_alert_style', models.CharField(choices=[('nav_left', 'Left of the Navbar'), ('nav_top', 'Top of the Navbar')], default='nav_left', help_text='Choose the style of active alerts', max_length=50, verbose_name='Active Alert Style')),
                ('site', models.OneToOneField(editable=False, on_delete=django.db.models.deletion.CASCADE, to='wagtailcore.site')),
            ],
            options={
                'verbose_name': 'Other Settings',
                'verbose_name_plural': 'Other Settings',
            },
        ),
    ]
