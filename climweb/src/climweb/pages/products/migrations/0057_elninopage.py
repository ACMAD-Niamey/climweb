import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0056_merge_0055_fix_rcc_service_icon_0055_productsubscriptionpage_form_open"),
    ]

    operations = [
        migrations.CreateModel(
            name="ElNinoPage",
            fields=[
                (
                    "productpage_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="products.productpage",
                    ),
                ),
                (
                    "africa_context",
                    wagtail.fields.RichTextField(
                        default=(
                            "<p>El Niño can shift rainfall and temperature patterns across Africa, with impacts that vary "
                            "by region and season. These changes can affect water availability, agriculture, food security, "
                            "health, energy and disaster risk.</p>"
                        ),
                        verbose_name="El Niño in Africa",
                    ),
                ),
                (
                    "acmad_response",
                    wagtail.fields.RichTextField(
                        default=(
                            "<p>ACMAD monitors ocean and atmosphere conditions, assesses likely impacts across African "
                            "regions, and works with Regional Climate Centres and National Meteorological and Hydrological "
                            "Services to turn the latest science into actionable climate information.</p>"
                        ),
                        verbose_name="What ACMAD is doing",
                    ),
                ),
                (
                    "bulletin_intro",
                    models.TextField(
                        default=(
                            "The monthly bulletin brings together the latest ENSO status, the outlook for Africa and "
                            "region-specific considerations for preparedness and early action."
                        ),
                        max_length=500,
                        verbose_name="Monthly bulletin introduction",
                    ),
                ),
            ],
            options={
                "verbose_name": "El Niño Page",
                "verbose_name_plural": "El Niño Pages",
            },
            bases=("products.productpage",),
        ),
    ]
