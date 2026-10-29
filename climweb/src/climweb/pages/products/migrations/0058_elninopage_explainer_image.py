import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0057_elninopage"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="elninopage",
            name="explainer_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Upload the image or infographic that explains El Niño.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="El Niño explainer image",
            ),
        ),
    ]
