from django.db import migrations, models


ROOT_CATALOGUE = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatedataservice/Synoptic_Daily_ARC2_Data/catalog.xml"
)


class Migration(migrations.Migration):
    dependencies = [("services", "0031_global_arc2_importer")]

    operations = [
        migrations.RemoveField(model_name="rccarc2importconfig", name="country"),
        migrations.AddField(
            model_name="rccarc2importconfig",
            name="singleton_key",
            field=models.CharField(default="arc2", editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="rccarc2importconfig",
            name="catalogue_url",
            field=models.URLField(default=ROOT_CATALOGUE, max_length=700),
        ),
    ]
