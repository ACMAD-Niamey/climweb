from django.db import migrations
from wagtail.fields import RichTextField


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0048_trainingtopic_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicepage",
            name="rationale_text",
            field=RichTextField(
                blank=True,
                help_text="Optional longer context displayed behind a Read full rationale button.",
                verbose_name="Full rationale",
            ),
        ),
    ]
