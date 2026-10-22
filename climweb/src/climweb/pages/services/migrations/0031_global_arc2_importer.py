from django.db import migrations, models
from django.utils import timezone


ROOT_CATALOGUE = (
    "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
    "climatedataservice/Synoptic_Daily_ARC2_Data/catalog.xml"
)


def consolidate_configs(apps, schema_editor):
    Config = apps.get_model("services", "RCCARC2ImportConfig")
    Run = apps.get_model("services", "RCCARC2ImportRun")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTasks = apps.get_model("django_celery_beat", "PeriodicTasks")

    configs = list(Config.objects.order_by("id"))
    if configs:
        canonical = next((item for item in configs if item.country == "Niger"), configs[0])
    else:
        canonical = Config.objects.create(country="Niger", catalogue_url=ROOT_CATALOGUE)
        configs = [canonical]

    selected = set()
    discovered = set()
    countries = set()
    for item in configs:
        countries.add(item.country)
        selected.update(f"{item.country}/{station}" for station in item.selected_stations)
        discovered.update(f"{item.country}/{station}" for station in item.discovered_stations)
        if item.pk != canonical.pk:
            Run.objects.filter(config_id=item.pk).update(config_id=canonical.pk)

    country_suffix = f"/{canonical.country}/catalog.xml"
    old_url = canonical.catalogue_url or ""
    canonical.catalogue_url = (
        f"{old_url[:-len(country_suffix)]}/catalog.xml"
        if old_url.endswith(country_suffix) else ROOT_CATALOGUE
    )
    canonical.selected_stations = sorted(selected)
    canonical.discovered_stations = sorted(discovered)
    canonical.discovered_countries = sorted(countries)
    canonical.import_all_stations = False
    canonical.enabled = False  # Explicit opt-in after consolidation.
    canonical.save()
    for run in Run.objects.filter(status="queued"):
        run.stations = [
            station if "/" in station else f"{run.country}/{station}"
            for station in run.stations
        ]
        suffix = f"/{run.country}/catalog.xml"
        if run.catalogue_url and run.catalogue_url.endswith(suffix):
            run.catalogue_url = f"{run.catalogue_url[:-len(suffix)]}/catalog.xml"
        run.save(update_fields=["stations", "catalogue_url"])
    Config.objects.exclude(pk=canonical.pk).delete()

    PeriodicTask.objects.filter(
        name__startswith="rcc-arc2-", name__endswith="-import"
    ).update(enabled=False)
    PeriodicTasks.objects.update_or_create(
        ident=1, defaults={"last_update": timezone.now()}
    )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0030_rcc_arc2_countries"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="rccarc2importconfig",
            name="import_all_stations",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="rccarc2importconfig",
            name="discovered_countries",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="rccarc2importrun",
            name="import_all_stations",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(consolidate_configs, migrations.RunPython.noop),
    ]
