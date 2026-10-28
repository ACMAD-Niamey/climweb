import uuid

from django.db import migrations


LEGACY_UPDATE_FIELDS = {
    "news": ("news", "hero_featured_news_id"),
    "news_2": ("news", "hero_featured_news_2_id"),
    "event": ("event", "hero_featured_event_id"),
    "event_2": ("event", "hero_featured_event_2_id"),
}


def reconcile_homepage_carousel_schema(apps, schema_editor):
    """Repair databases whose migration ledger is ahead of their schema.

    Some restored development databases record migration 0054 as applied while
    retaining the legacy carousel columns. In that state Django cannot even
    load a HomePage because ``hero_featured_updates`` is missing.
    """
    HomePage = apps.get_model("home", "HomePage")
    connection = schema_editor.connection
    table_name = HomePage._meta.db_table

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if "hero_featured_updates" in columns:
        return

    legacy_columns = {
        field_name
        for _, field_name in LEGACY_UPDATE_FIELDS.values()
        if field_name in columns
    }
    selected_columns = ["page_ptr_id"]
    if "hero_carousel_order" in columns:
        selected_columns.append("hero_carousel_order")
    selected_columns.extend(sorted(legacy_columns))

    quote_name = connection.ops.quote_name
    select_sql = "SELECT {} FROM {}".format(
        ", ".join(quote_name(column) for column in selected_columns),
        quote_name(table_name),
    )
    with connection.cursor() as cursor:
        cursor.execute(select_sql)
        legacy_rows = [dict(zip(selected_columns, row)) for row in cursor.fetchall()]

    schema_editor.add_field(
        HomePage,
        HomePage._meta.get_field("hero_featured_updates"),
    )

    default_order = ["news", "news_2", "event", "event_2"]
    for row in legacy_rows:
        order_value = row.get("hero_carousel_order") or []
        order = [item.get("type") for item in order_value if isinstance(item, dict)]
        if not order:
            order = default_order

        updates = []
        for slot in order:
            field_config = LEGACY_UPDATE_FIELDS.get(slot)
            if not field_config:
                continue
            block_type, field_name = field_config
            page_id = row.get(field_name)
            if page_id:
                updates.append({
                    "type": block_type,
                    "value": page_id,
                    "id": str(uuid.uuid4()),
                })

        HomePage.objects.filter(pk=row["page_ptr_id"]).update(
            hero_featured_updates=updates[:5]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0054_remove_homepage_hero_carousel_order_and_more"),
    ]

    operations = [
        migrations.RunPython(
            reconcile_homepage_carousel_schema,
            migrations.RunPython.noop,
        ),
    ]
