from django.db import migrations


def rename_generic_bulletin(apps, schema_editor):
    ProductItemPage = apps.get_model('products', 'ProductItemPage')

    for bulletin in ProductItemPage.objects.filter(
        title__in=["El-nino Monthly Bulletin", "El Niño Monthly Bulletin"],
    ):
        bulletin.title = "ENSO Monthly Bulletin"
        if bulletin.draft_title in ["El-nino Monthly Bulletin", "El Niño Monthly Bulletin"]:
            bulletin.draft_title = "ENSO Monthly Bulletin"
            bulletin.save(update_fields=['title', 'draft_title'])
        else:
            bulletin.save(update_fields=['title'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0060_update_legacy_enso_richtext'),
    ]

    operations = [
        migrations.RunPython(rename_generic_bulletin, migrations.RunPython.noop),
    ]
