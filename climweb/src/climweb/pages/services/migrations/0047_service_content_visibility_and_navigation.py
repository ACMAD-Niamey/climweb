import uuid

from django.db import migrations, models


RCC_NAME = "Regional Climate Center"


def configure_service_navigation(apps, schema_editor):
    ServicePage = apps.get_model("services", "ServicePage")
    Page = apps.get_model("wagtailcore", "Page")
    NavigationSettings = apps.get_model("base", "NavigationSettings")

    ServicePage.objects.filter(slug="cuip").update(
        show_projects_section=False,
        show_events_section=False,
    )

    rcc = ServicePage.objects.filter(service__name__iexact=RCC_NAME).first()
    if not rcc:
        return

    Page.objects.filter(pk=rcc.pk).update(show_in_menus=False)

    for navigation in NavigationSettings.objects.all():
        menu = list(navigation.main_menu.raw_data or [])
        has_top_level_rcc = False
        services_position = len(menu)

        for position, block in enumerate(menu):
            value = block.get("value", {})
            if value.get("page") == rcc.pk or value.get("label", "").casefold() == RCC_NAME.casefold():
                has_top_level_rcc = True
            if value.get("label", "").casefold() == "services":
                services_position = position + 1
                value["sub_items"] = [
                    item for item in value.get("sub_items", [])
                    if item.get("value", {}).get("page") != rcc.pk
                    and item.get("value", {}).get("label", "").casefold() != RCC_NAME.casefold()
                ]

        if not has_top_level_rcc:
            menu.insert(services_position, {
                "id": str(uuid.uuid4()),
                "type": "navigation_item",
                "value": {
                    "page": rcc.pk,
                    "label": RCC_NAME,
                    "sub_items": [],
                    "external_url": "",
                    "large_submenu": False,
                    "include_subpages": False,
                },
            })
        navigation.main_menu = menu
        navigation.save(update_fields=["main_menu"])


def reverse_service_navigation(apps, schema_editor):
    ServicePage = apps.get_model("services", "ServicePage")
    Page = apps.get_model("wagtailcore", "Page")
    NavigationSettings = apps.get_model("base", "NavigationSettings")

    ServicePage.objects.filter(slug="cuip").update(
        show_projects_section=True,
        show_events_section=True,
    )

    rcc = ServicePage.objects.filter(service__name__iexact=RCC_NAME).first()
    if not rcc:
        return

    Page.objects.filter(pk=rcc.pk).update(show_in_menus=True)
    for navigation in NavigationSettings.objects.all():
        navigation.main_menu = [
            block for block in list(navigation.main_menu.raw_data or [])
            if block.get("value", {}).get("page") != rcc.pk
            and block.get("value", {}).get("label", "").casefold() != RCC_NAME.casefold()
        ]
        navigation.save(update_fields=["main_menu"])


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0053_merge_20260922_0830"),
        ("services", "0046_rcccoordinationpage"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicepage",
            name="show_events_section",
            field=models.BooleanField(default=True, verbose_name="Show events section"),
        ),
        migrations.AddField(
            model_name="servicepage",
            name="show_news_section",
            field=models.BooleanField(default=True, verbose_name="Show news section"),
        ),
        migrations.AddField(
            model_name="servicepage",
            name="show_projects_section",
            field=models.BooleanField(default=True, verbose_name="Show projects section"),
        ),
        migrations.AddField(
            model_name="servicepage",
            name="show_publications_section",
            field=models.BooleanField(default=True, verbose_name="Show publications section"),
        ),
        migrations.RunPython(configure_service_navigation, reverse_service_navigation),
    ]
