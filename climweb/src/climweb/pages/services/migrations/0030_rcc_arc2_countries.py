from django.db import migrations, models
from django.core.management.color import no_style


NIGER_CATALOGUE = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatedataservice/Synoptic_Daily_ARC2_Data/Niger/catalog.xml"
)


def backfill_niger_run_urls(apps, schema_editor):
    runs = apps.get_model("services", "RCCARC2ImportRun")
    runs.objects.filter(catalogue_url="").update(catalogue_url=NIGER_CATALOGUE)


def reset_config_sequence(apps, schema_editor):
    config = apps.get_model("services", "RCCARC2ImportConfig")
    for statement in schema_editor.connection.ops.sequence_reset_sql(no_style(), [config]):
        schema_editor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [("services", "0029_rcc_arc2_importer")]

    operations = [
        migrations.AddField(
            model_name="rccarc2importconfig",
            name="country",
            field=models.CharField(default="Niger", max_length=80, unique=True),
        ),
        migrations.AddField(
            model_name="rccarc2importconfig",
            name="catalogue_url",
            field=models.URLField(default=NIGER_CATALOGUE, max_length=700),
        ),
        migrations.AddField(
            model_name="rccarc2importrun",
            name="country",
            field=models.CharField(default="Niger", max_length=80),
        ),
        migrations.AddField(
            model_name="rccarc2importrun",
            name="catalogue_url",
            field=models.URLField(blank=True, max_length=700),
        ),
        migrations.RunPython(backfill_niger_run_urls, migrations.RunPython.noop),
        migrations.RunPython(reset_config_sequence, migrations.RunPython.noop),
    ]
