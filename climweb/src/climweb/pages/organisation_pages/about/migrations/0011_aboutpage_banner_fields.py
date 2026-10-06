from django.db import migrations, models
import django.db.models.deletion


def copy_page_titles_to_banner(apps, schema_editor):
    AboutPage = apps.get_model("about", "AboutPage")
    for page in AboutPage.objects.select_related("page_ptr"):
        page.banner_title = page.page_ptr.title
        page.save(update_fields=["banner_title"])


class Migration(migrations.Migration):

    dependencies = [
        ("about", "0010_alter_aboutpage_introduction_button_text"),
        ("wagtailcore", "0093_uploadedfile"),
        ("wagtailimages", "0026_delete_uploadedimage"),
    ]

    operations = [
        migrations.AddField(
            model_name="aboutpage",
            name="banner_image",
            field=models.ForeignKey(
                blank=True,
                help_text="A high quality banner image",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Banner Image",
            ),
        ),
        migrations.AddField(
            model_name="aboutpage",
            name="banner_subtitle",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Banner Subtitle",
            ),
        ),
        migrations.AddField(
            model_name="aboutpage",
            name="banner_title",
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name="Banner Title",
            ),
        ),
        migrations.RunPython(copy_page_titles_to_banner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="aboutpage",
            name="banner_title",
            field=models.CharField(max_length=255, verbose_name="Banner Title"),
        ),
        migrations.AddField(
            model_name="aboutpage",
            name="call_to_action_button_text",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Call to action button text",
            ),
        ),
        migrations.AddField(
            model_name="aboutpage",
            name="call_to_action_related_page",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailcore.page",
                verbose_name="Call to action related page",
            ),
        ),
    ]
