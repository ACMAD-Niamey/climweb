import json
import uuid
from pathlib import Path

from django.db import migrations


DIRECTORY_BLOCK_VALUE = {
    "heading": "African National Meteorological Services",
    "introduction": (
        "Explore the official meteorological and hydrological services serving countries across Africa."
    ),
    "show_search": True,
}


def seed_african_met_services(apps, schema_editor):
    MeteorologicalService = apps.get_model("services", "MeteorologicalService")
    FlexPage = apps.get_model("flex_page", "FlexPage")
    data_path = Path(__file__).resolve().parents[1] / "data" / "african_met_services.json"
    inventory = json.loads(data_path.read_text(encoding="utf-8"))

    for order, item in enumerate(inventory, start=1):
        MeteorologicalService.objects.get_or_create(
            wmo_member_id=item["wmo_member_id"],
            defaults={
                "country": item["country"],
                "name": item["name"],
                "acronym": item.get("acronym", ""),
                "website_url": item["website_url"],
                "logo_source_url": item.get("logo_source_url", ""),
                "order": order,
                "is_active": True,
            },
        )

    page = FlexPage.objects.filter(title__iexact="Met Services").first()
    if page:
        existing_content = page.content or []
        if not any(block.block_type == "met_services_directory" for block in existing_content):
            raw_content = list(page.content.raw_data) if page.content else []
            raw_content.append(
                {
                    "type": "met_services_directory",
                    "value": DIRECTORY_BLOCK_VALUE,
                    "id": str(uuid.uuid4()),
                }
            )
            page.content = raw_content
            page.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0015_meteorologicalservice"),
        ("flex_page", "0005_alter_flexpage_content"),
    ]

    operations = [
        migrations.RunPython(seed_african_met_services, migrations.RunPython.noop),
    ]
