import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0003_staffmember_linkedin_staffmember_website_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffEmployment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("active", "Current"), ("retired", "Retired"), ("left", "Left")], default="active", max_length=12)),
                ("effective_date", models.DateField()),
                ("member", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="employment", to="staff.staffmember")),
            ],
        ),
        migrations.CreateModel(
            name="StaffEmploymentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(choices=[("active", "Current"), ("retired", "Retired"), ("left", "Left")], max_length=12)),
                ("status", models.CharField(choices=[("active", "Current"), ("retired", "Retired"), ("left", "Left")], max_length=12)),
                ("effective_date", models.DateField()),
                ("account_disabled", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staff_employment_events", to=settings.AUTH_USER_MODEL)),
                ("employment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="staff.staffemployment")),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AlterField(
            model_name="staffprofileupdate", name="status",
            field=models.CharField(choices=[("draft", "Draft"), ("submitted", "Awaiting review"), ("approved", "Approved"), ("changes_requested", "Changes requested"), ("withdrawn", "Withdrawn on offboarding")], default="draft", max_length=24),
        ),
    ]
