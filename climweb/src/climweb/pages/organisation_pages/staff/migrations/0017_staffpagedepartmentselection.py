import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0016_alter_staffnotificationdelivery_event_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffPageDepartmentSelection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sort_order",
                    models.IntegerField(blank=True, editable=False, null=True),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_page_selections",
                        to="staff.department",
                        verbose_name="Department",
                    ),
                ),
                (
                    "page",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="selected_departments",
                        to="staff.staffpage",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "pk"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("page", "department"),
                        name="unique_staff_page_department",
                    )
                ],
            },
        ),
    ]
