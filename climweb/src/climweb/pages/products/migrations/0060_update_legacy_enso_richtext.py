from django.db import migrations


OLD_INTRODUCTION_TEXT = (
    "El Niño is a warming of the central and eastern tropical Pacific Ocean that can influence "
    "weather patterns around the world. Across Africa, its effects are not uniform: the timing, "
    "strength and location of rainfall and temperature changes differ between regions and seasons."
)
NEW_INTRODUCTION_TEXT = (
    "The El Niño–Southern Oscillation (ENSO) is a recurring variation in tropical Pacific Ocean "
    "temperatures and atmospheric circulation. Its El Niño, La Niña and neutral phases can influence "
    "weather patterns around the world. Across Africa, ENSO effects are not uniform: the timing, "
    "strength and location of rainfall and temperature changes differ between regions and seasons."
)
OLD_AFRICA_CONTEXT_TEXT = (
    "El Niño can shift rainfall and temperature patterns across Africa, with impacts that vary "
    "by region and season. These changes can affect water availability, agriculture, food security, "
    "health, energy and disaster risk."
)
NEW_AFRICA_CONTEXT_TEXT = (
    "ENSO can shift rainfall and temperature patterns across Africa through its El Niño, La Niña "
    "and neutral phases. The effects vary by region and season and can influence water availability, "
    "agriculture, food security, health, energy and disaster risk."
)


def update_legacy_richtext(apps, schema_editor):
    ElNinoPage = apps.get_model('products', 'ElNinoPage')

    for page in ElNinoPage.objects.all():
        changed = []
        introduction = str(page.introduction_text)
        if OLD_INTRODUCTION_TEXT in introduction:
            page.introduction_text = introduction.replace(OLD_INTRODUCTION_TEXT, NEW_INTRODUCTION_TEXT)
            changed.append('introduction_text')

        africa_context = str(page.africa_context)
        if OLD_AFRICA_CONTEXT_TEXT in africa_context:
            page.africa_context = africa_context.replace(OLD_AFRICA_CONTEXT_TEXT, NEW_AFRICA_CONTEXT_TEXT)
            changed.append('africa_context')

        if changed:
            page.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0059_alter_elninopage_options_and_more'),
    ]

    operations = [
        migrations.RunPython(update_legacy_richtext, migrations.RunPython.noop),
    ]
