# Generated by Django 4.2.7 on 2024-08-10 07:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("aviation", "0008_rename_stationcategory_airportcategory"),
    ]

    operations = [
        migrations.AlterField(
            model_name="airport",
            name="id",
            field=models.CharField(
                help_text="The ICAO airport code or location indicator is a four-letter code designating aerodromes around the world.",
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ICAO Code",
            ),
        ),
    ]
