import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("summer_school", "0016_summerschoolpage_online_meeting_button_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="summerschoolpage",
            name="gallery_title",
            field=models.CharField(
                default="Gallery",
                max_length=255,
                verbose_name="Gallery Title",
            ),
        ),
        migrations.AddField(
            model_name="summerschoolpage",
            name="gallery_intro",
            field=wagtail.fields.RichTextField(
                blank=True,
                verbose_name="Gallery Introduction",
            ),
        ),
        migrations.AddField(
            model_name="summerschoolpage",
            name="gallery_images",
            field=wagtail.fields.StreamField(
                [("image", 2)],
                blank=True,
                block_lookup={
                    0: (
                        "wagtail.images.blocks.ImageChooserBlock",
                        (),
                        {"help_text": "Select or upload a gallery image"},
                    ),
                    1: (
                        "wagtail.blocks.CharBlock",
                        (),
                        {
                            "help_text": "Optional caption or photo credit",
                            "max_length": 255,
                            "required": False,
                        },
                    ),
                    2: (
                        "wagtail.blocks.StructBlock",
                        [[("image", 0), ("caption", 1)]],
                        {},
                    ),
                },
                verbose_name="Gallery Images",
            ),
        ),
    ]
