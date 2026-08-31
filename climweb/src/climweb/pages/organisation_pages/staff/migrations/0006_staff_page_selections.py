import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


def copy_staff_selections(apps, schema_editor):
    alias = schema_editor.connection.alias
    Member = apps.get_model("staff", "StaffMember")
    Selection = apps.get_model("staff", "StaffPageSelection")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")
    selections = {}
    for member in Member.objects.using(alias).order_by("sort_order", "pk").iterator():
        selection = Selection.objects.using(alias).create(page_id=member.page_id, member_id=member.pk, sort_order=member.sort_order)
        selections[(member.page_id, member.pk)] = selection.pk
    content_type = ContentType.objects.using(alias).filter(app_label="staff", model="staffpage").first()
    if not content_type:
        return
    # Preserve each revision's own membership and ordering, including pending
    # drafts. Keep all original staff content; no accounts/profiles are deleted.
    for revision in Revision.objects.using(alias).filter(content_type_id=content_type.pk).iterator():
        content = dict(revision.content)
        if "selected_staff" in content:
            continue
        page_id = int(revision.object_id)
        content["selected_staff"] = [
            {"pk": selections[(page_id, member["pk"])], "page": page_id,
             "member": member["pk"], "sort_order": member.get("sort_order", index)}
            for index, member in enumerate(content.get("staffmembers", []))
            if (page_id, member.get("pk")) in selections
        ]
        revision.content = content
        revision.save(using=alias, update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [("staff", "0005_staff_contact_links")]

    operations = [
        migrations.CreateModel(
            name="StaffPageSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="page_selections", to="staff.staffmember", verbose_name="Staff member")),
                ("page", modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name="selected_staff", to="staff.staffpage")),
            ],
            options={"ordering": ["sort_order", "pk"]},
        ),
        migrations.RunPython(copy_staff_selections, migrations.RunPython.noop),
    ]
