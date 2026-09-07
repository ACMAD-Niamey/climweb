from decimal import Decimal

import django.core.validators
from django.db import migrations, models


DEFAULT_CENTRES = (
    {
        "display_name": "RCC-Network NA",
        "full_name": "RCC-Network Northern Africa",
        "city": "Casablanca",
        "country": "Morocco",
        "website_url": "http://rccnara1.marocmeteo.ma/",
        "status": "designated",
        "map_x": Decimal("34.5"),
        "map_y": Decimal("15.9"),
        "label_position": "lower_right",
        "order": 10,
    },
    {
        "display_name": "ACMAD · RCC Africa",
        "full_name": "ACMAD Regional Climate Centre for Africa",
        "city": "Niamey",
        "country": "Niger",
        "website_url": "https://new-rcc.acmad.org/",
        "status": "designated",
        "map_x": Decimal("68.3"),
        "map_y": Decimal("92.6"),
        "label_position": "upper_right",
        "is_primary": True,
        "order": 20,
    },
    {
        "display_name": "AGRHYMET · RCC WAS",
        "full_name": "AGRHYMET RCC West Africa and the Sahel",
        "city": "Niamey",
        "country": "Niger",
        "website_url": "https://agrhymet.cilss.int/",
        "status": "demonstration",
        "map_x": Decimal("72.8"),
        "map_y": Decimal("97.1"),
        "label_position": "lower_right",
        "order": 30,
    },
    {
        "display_name": "CAPC-AC · RCC ECCAS",
        "full_name": "CAPC-AC RCC for Economic Community of Central African States",
        "city": "Yaoundé",
        "country": "Cameroon",
        "website_url": "https://capc-ac.net/",
        "status": "demonstration",
        "map_x": Decimal("100.9"),
        "map_y": Decimal("126.7"),
        "label_position": "lower_left",
        "order": 40,
    },
    {
        "display_name": "ICPAC · RCC IGAD",
        "full_name": "ICPAC RCC for Inter-Governmental Authority on Development",
        "city": "Nairobi",
        "country": "Kenya",
        "website_url": "https://www.icpac.net/",
        "status": "designated",
        "map_x": Decimal("189.0"),
        "map_y": Decimal("144.6"),
        "label_position": "lower_right",
        "order": 50,
    },
    {
        "display_name": "SADC-CSC · RCC SADC",
        "full_name": "SADC Climate Services Centre RCC",
        "city": "Gaborone",
        "country": "Botswana",
        "website_url": "https://csc.sadc.int/",
        "status": "demonstration",
        "map_x": Decimal("151.1"),
        "map_y": Decimal("228.6"),
        "label_position": "upper_left",
        "order": 60,
    },
)


def seed_regional_climate_centres(apps, schema_editor):
    RegionalClimateCentre = apps.get_model("home", "RegionalClimateCentre")

    for centre in DEFAULT_CENTRES:
        defaults = {"is_active": True, "is_primary": False, **centre}
        display_name = defaults.pop("display_name")
        RegionalClimateCentre.objects.get_or_create(display_name=display_name, defaults=defaults)


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0042_homepage_dg_message_homepage_dg_message_closing_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegionalClimateCentre",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(help_text="Short centre name displayed beside the map marker.", max_length=100, unique=True, verbose_name="Map label")),
                ("full_name", models.CharField(max_length=255, verbose_name="Full name")),
                ("city", models.CharField(max_length=100, verbose_name="City")),
                ("country", models.CharField(max_length=100, verbose_name="Country")),
                ("website_url", models.URLField(help_text="Official website opened when the marker is selected.", max_length=500, verbose_name="Website URL")),
                ("status", models.CharField(choices=[("designated", "WMO designated"), ("demonstration", "In demonstration")], default="designated", max_length=20, verbose_name="RCC status")),
                ("map_x", models.DecimalField(decimal_places=1, help_text="SVG horizontal coordinate from 0 (left) to 240 (right).", max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(240)], verbose_name="Horizontal map position")),
                ("map_y", models.DecimalField(decimal_places=1, help_text="SVG vertical coordinate from 0 (top) to 270 (bottom).", max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(270)], verbose_name="Vertical map position")),
                ("label_position", models.CharField(choices=[("upper_right", "Upper right"), ("lower_right", "Lower right"), ("upper_left", "Upper left"), ("lower_left", "Lower left")], default="lower_right", max_length=20, verbose_name="Label position")),
                ("is_primary", models.BooleanField(default=False, help_text="Keep this centre's label visible when the map is not being hovered.", verbose_name="Keep label visible")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Display order")),
                ("is_active", models.BooleanField(default=True, verbose_name="Visible on homepage")),
            ],
            options={
                "verbose_name": "Regional Climate Centre",
                "verbose_name_plural": "Regional Climate Centres",
                "ordering": ("order", "display_name"),
            },
        ),
        migrations.RunPython(seed_regional_climate_centres, migrations.RunPython.noop),
    ]
