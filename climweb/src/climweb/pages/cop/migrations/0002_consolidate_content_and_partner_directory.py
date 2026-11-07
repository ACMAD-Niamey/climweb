import re

import django.db.models.deletion
import modelcluster.fields
import wagtail.fields
from django.db import migrations, models


def _section(value):
    value = str(value or "").strip()
    return value


def consolidate_cop_content(apps, schema_editor):
    CopEditionPage = apps.get_model("cop", "CopEditionPage")
    CopSideEventPage = apps.get_model("cop", "CopSideEventPage")
    Partner = apps.get_model("partners", "Partner")

    for edition in CopEditionPage.objects.all():
        edition.description = "".join((
            _section(edition.acmad_participation),
            _section(edition.about),
            _section(edition.objectives),
            _section(edition.expected_outcomes),
        ))
        edition.save(update_fields=["description"])

    for event in CopSideEventPage.objects.all():
        event.description = "".join((
            str(event.summary or "").strip(),
            str(event.description or "").strip(),
            _section(event.objectives),
        ))
        event.save(update_fields=["description"])

        selected_partner_ids = set()
        try:
            embedded_partners = list(event.partners)
        except (TypeError, ValueError):
            embedded_partners = []

        for block in embedded_partners:
            value = block.value
            name = str(value.get("name") or "").strip()
            if not name:
                continue
            partner = Partner.objects.filter(name__iexact=name).first()
            if not partner:
                logo = value.get("logo")
                partner = Partner.objects.create(
                    name=name[:100],
                    logo_id=getattr(logo, "pk", logo) or None,
                    link=value.get("website_url") or None,
                )
            selected_partner_ids.add(partner.pk)

        participant_text = re.sub(r"<[^>]+>", " ", str(event.participants or ""))
        participant_text = re.sub(r"\s+", " ", participant_text).lower()
        if participant_text:
            for partner in Partner.objects.all():
                if partner.name.lower() in participant_text:
                    selected_partner_ids.add(partner.pk)

        if selected_partner_ids:
            event.directory_partners.add(*Partner.objects.filter(pk__in=selected_partner_ids))


class Migration(migrations.Migration):

    dependencies = [
        ("cop", "0001_initial"),
        ("partners", "0005_alter_partnerspage_introduction_text_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="copeditionpage",
            name="description",
            field=wagtail.fields.RichTextField(
                default="",
                help_text="Combine ACMAD's participation, background, objectives and expected outcomes in this field.",
                verbose_name="Description",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="copsideeventpage",
            name="lead_organizer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cop_side_events_led",
                to="partners.partner",
                verbose_name="Lead organizer",
            ),
        ),
        migrations.AddField(
            model_name="copsideeventpage",
            name="theme",
            field=models.CharField(blank=True, max_length=255, verbose_name="Theme"),
        ),
        migrations.AddField(
            model_name="copsideeventpage",
            name="directory_partners",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                help_text="Select partner organisations from the central Partners list.",
                related_name="cop_side_events_pending",
                to="partners.partner",
                verbose_name="Partners",
            ),
        ),
        migrations.AlterField(
            model_name="copeditionpage",
            name="schedule_documents",
            field=wagtail.fields.StreamField(
                [("document", 4)],
                blank=True,
                block_lookup={
                    0: ("wagtail.blocks.CharBlock", (), {"max_length": 220}),
                    1: ("wagtail.documents.blocks.DocumentChooserBlock", (), {}),
                    2: ("wagtail.images.blocks.ImageChooserBlock", (), {"help_text": "Flyer preview displayed in the schedule carousel.", "required": False}),
                    3: ("wagtail.blocks.CharBlock", (), {"max_length": 300, "required": False}),
                    4: ("wagtail.blocks.StructBlock", [[("title", 0), ("document", 1), ("preview_image", 2), ("description", 3)]], {}),
                },
                verbose_name="Schedules and programme documents",
            ),
        ),
        migrations.AlterField(
            model_name="copsideeventpage",
            name="additional_documents",
            field=wagtail.fields.StreamField(
                [("document", 4)],
                blank=True,
                block_lookup={
                    0: ("wagtail.blocks.CharBlock", (), {"max_length": 220}),
                    1: ("wagtail.documents.blocks.DocumentChooserBlock", (), {}),
                    2: ("wagtail.images.blocks.ImageChooserBlock", (), {"help_text": "Flyer preview displayed in the schedule carousel.", "required": False}),
                    3: ("wagtail.blocks.CharBlock", (), {"max_length": 300, "required": False}),
                    4: ("wagtail.blocks.StructBlock", [[("title", 0), ("document", 1), ("preview_image", 2), ("description", 3)]], {}),
                },
                verbose_name="Other documents",
            ),
        ),
        migrations.AlterField(
            model_name="copsideeventpage",
            name="presentations",
            field=wagtail.fields.StreamField(
                [("presentation", 4)],
                blank=True,
                block_lookup={
                    0: ("wagtail.blocks.CharBlock", (), {"max_length": 220}),
                    1: ("wagtail.documents.blocks.DocumentChooserBlock", (), {}),
                    2: ("wagtail.images.blocks.ImageChooserBlock", (), {"help_text": "Flyer preview displayed in the schedule carousel.", "required": False}),
                    3: ("wagtail.blocks.CharBlock", (), {"max_length": 300, "required": False}),
                    4: ("wagtail.blocks.StructBlock", [[("title", 0), ("document", 1), ("preview_image", 2), ("description", 3)]], {}),
                },
                verbose_name="Presentation documents",
            ),
        ),
        migrations.RunPython(consolidate_cop_content, migrations.RunPython.noop),
        migrations.RemoveField(model_name="copeditionpage", name="about"),
        migrations.RemoveField(model_name="copeditionpage", name="acmad_participation"),
        migrations.RemoveField(model_name="copeditionpage", name="expected_outcomes"),
        migrations.RemoveField(model_name="copeditionpage", name="objectives"),
        migrations.RemoveField(model_name="copsideeventpage", name="objectives"),
        migrations.RemoveField(model_name="copsideeventpage", name="participants"),
        migrations.RemoveField(model_name="copsideeventpage", name="summary"),
        migrations.RemoveField(model_name="copsideeventpage", name="partners"),
        migrations.RenameField(
            model_name="copsideeventpage",
            old_name="directory_partners",
            new_name="partners",
        ),
        migrations.AlterField(
            model_name="copsideeventpage",
            name="partners",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                help_text="Select partner organisations from the central Partners list.",
                related_name="cop_side_events",
                to="partners.partner",
                verbose_name="Partners",
            ),
        ),
        migrations.AlterField(
            model_name="copsideeventpage",
            name="description",
            field=wagtail.fields.RichTextField(
                help_text="Combine the summary, detailed description and objectives here.",
                verbose_name="Description",
            ),
        ),
    ]
