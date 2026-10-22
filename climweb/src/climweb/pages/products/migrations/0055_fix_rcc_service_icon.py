from django.db import migrations


def fix_rcc_service_icon(apps, schema_editor):
    ServiceCategory = apps.get_model("base", "ServiceCategory")
    ServiceCategory.objects.filter(
        name="Regional Climate Center",
        icon="cloud-sun-rain",
    ).update(icon="globe")


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0054_productsubscriber_extra_data_productsubscriptionpage_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_rcc_service_icon, migrations.RunPython.noop),
    ]
