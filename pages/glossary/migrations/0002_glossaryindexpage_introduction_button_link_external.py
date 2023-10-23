# Generated by Django 4.2.3 on 2023-10-23 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('glossary', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='glossaryindexpage',
            name='introduction_button_link_external',
            field=models.URLField(blank=True, help_text='External Link if applicable. Ignored if internal page above is chosen', null=True),
        ),
    ]
