from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("staff", "0004_staff_employment")]

    operations = [
        migrations.AddField(model_name="staffmember", name="github", field=models.URLField(blank=True, verbose_name="GitHub profile")),
        migrations.AddField(model_name="staffmember", name="publications", field=models.URLField(blank=True, verbose_name="Publications URL", help_text="Link to Google Scholar, ORCID or your publications page.")),
        migrations.AddField(model_name="staffmember", name="public_email", field=models.EmailField(blank=True, max_length=254, verbose_name="Public contact email", help_text="Optional. Published on the website; separate from your private account email.")),
        migrations.AddField(model_name="staffprofileupdate", name="github", field=models.URLField(blank=True)),
        migrations.AddField(model_name="staffprofileupdate", name="publications", field=models.URLField(blank=True)),
        migrations.AddField(model_name="staffprofileupdate", name="public_email", field=models.EmailField(blank=True, max_length=254)),
    ]
