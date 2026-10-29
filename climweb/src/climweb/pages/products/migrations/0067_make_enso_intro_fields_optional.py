import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0066_elninopage_secondary_section"),
    ]

    operations = [
        migrations.AlterField(
            model_name="elninopage",
            name="acmad_response",
            field=wagtail.fields.RichTextField(
                blank=True,
                default=(
                    "<p>These phases can influence rainfall and temperature across Africa, but their effects "
                    "vary by region and season and must be considered alongside other climate drivers.</p>"
                ),
                verbose_name="ENSO explanation — African impacts",
            ),
        ),
        migrations.AlterField(
            model_name="elninopage",
            name="africa_context",
            field=wagtail.fields.RichTextField(
                blank=True,
                default=(
                    "<p>ENSO links changes in the tropical Pacific Ocean with the atmosphere. El Niño is the "
                    "warm phase, La Niña the cool phase, and neutral conditions occur between them.</p>"
                ),
                verbose_name="ENSO explanation — phases",
            ),
        ),
        migrations.AlterField(
            model_name="elninopage",
            name="bulletin_intro",
            field=models.TextField(
                blank=True,
                default=(
                    "The monthly bulletin brings together the latest ENSO status, the outlook for Africa and "
                    "region-specific considerations for preparedness and early action."
                ),
                max_length=500,
                verbose_name="Monthly bulletin introduction",
            ),
        ),
    ]
