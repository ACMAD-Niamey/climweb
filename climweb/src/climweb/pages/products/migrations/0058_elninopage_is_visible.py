from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0057_elninopage"),
    ]

    operations = [
        migrations.AddField(
            model_name="elninopage",
            name="is_visible",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Untick to hide the El Niño page, its bulletins, and its homepage carousel slide. "
                    "Editors can still preview the page in Wagtail."
                ),
                verbose_name="Visible on website",
            ),
        ),
    ]
