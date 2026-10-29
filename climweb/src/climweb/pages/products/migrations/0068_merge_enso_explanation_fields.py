from html import escape

import wagtail.fields
from django.db import migrations


DEFAULT_ENSO_EXPLANATION = (
    "<p>ENSO links changes in the tropical Pacific Ocean with the atmosphere. El Niño is the warm phase, "
    "La Niña the cool phase, and neutral conditions occur between them.</p>"
    "<p>These phases can influence rainfall and temperature across Africa, but their effects vary by "
    "region and season and must be considered alongside other climate drivers.</p>"
    "<p>The monthly bulletin brings together the latest ENSO status, the outlook for Africa and "
    "region-specific considerations for preparedness and early action.</p>"
)


def combine_enso_explanation(apps, schema_editor):
    ElNinoPage = apps.get_model("products", "ElNinoPage")

    for page in ElNinoPage.objects.all():
        sections = []
        for value in (page.africa_context, page.acmad_response):
            content = str(value).strip()
            if content:
                sections.append(content)

        bulletin_intro = str(page.bulletin_intro).strip()
        if bulletin_intro:
            if bulletin_intro.startswith("<"):
                sections.append(bulletin_intro)
            else:
                sections.append(f"<p>{escape(bulletin_intro)}</p>")

        page.enso_explanation = "".join(sections)
        page.save(update_fields=["enso_explanation"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0067_make_enso_intro_fields_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="elninopage",
            name="enso_explanation",
            field=wagtail.fields.RichTextField(
                blank=True,
                default=DEFAULT_ENSO_EXPLANATION,
                help_text="Use this single section for ENSO phases, African impacts and bulletin context.",
                verbose_name="ENSO explanation",
            ),
        ),
        migrations.RunPython(combine_enso_explanation, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="elninopage",
            name="acmad_response",
        ),
        migrations.RemoveField(
            model_name="elninopage",
            name="africa_context",
        ),
        migrations.RemoveField(
            model_name="elninopage",
            name="bulletin_intro",
        ),
    ]
