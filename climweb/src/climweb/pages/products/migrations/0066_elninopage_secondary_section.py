import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0065_alter_elninopage_acmad_response_and_more"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="elninopage",
            name="secondary_section_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Displayed on the right side of the additional ENSO content section.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Additional section image",
            ),
        ),
        migrations.AddField(
            model_name="elninopage",
            name="secondary_section_image_caption",
            field=models.CharField(
                blank=True,
                help_text="Optional caption displayed directly below the image.",
                max_length=500,
                verbose_name="Additional section image caption",
            ),
        ),
        migrations.AddField(
            model_name="elninopage",
            name="secondary_section_text",
            field=wagtail.fields.RichTextField(
                blank=True,
                verbose_name="Additional section text",
            ),
        ),
        migrations.AddField(
            model_name="elninopage",
            name="secondary_section_title",
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name="Additional section title",
            ),
        ),
    ]
