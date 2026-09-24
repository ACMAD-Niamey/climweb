from django.core.management.base import BaseCommand
from wagtail.documents import get_document_model
from wagtail.models import Site

from climweb.base.models import NavigationSettings
from climweb.pages.services.models import (
    OnTheJobTrainingPage,
    RCCTrainingPage,
    ServicePage,
)
from climweb.pages.services.training_resources import RCC_TRAINING_DOCUMENTS


METHODOLOGY_GROUPS = (
    (
        "climate-data-procedures",
        "Climate data procedures and indices",
        "Quality control, CPT preparation, GTS ingestion and guidance for climate indices.",
        "tasks",
    ),
    (
        "data-rescue",
        "Data rescue",
        "Practical references for locating, preserving, imaging and digitising historical observations.",
        "download",
    ),
    (
        "climsoft-data-management",
        "Climsoft data management",
        "Installation, administration, development, data entry and operational user guidance.",
        "database",
    ),
)

REPORT_GROUPS = (
    (
        "workshop-reports",
        "Climate Outlook Forum reports",
        "Reports from regional and sub-regional seasonal forecast workshops and forums.",
        "group",
    ),
    (
        "training-reports",
        "Trainee and scientific-stay reports",
        "Learning outputs and reports prepared through ACMAD placements and scientific stays.",
        "user",
    ),
    (
        "surveys-and-analysis",
        "Surveys and analysis",
        "Questionnaires, needs assessments and supporting proposals for regional training activities.",
        "form",
    ),
)


def resource_groups(definitions):
    Document = get_document_model()
    available_documents = list(Document.objects.all())
    documents = {document.title: document for document in available_documents}
    groups = []
    for anchor, title, description, icon in definitions:
        resources = []
        for record in RCC_TRAINING_DOCUMENTS:
            if record["group"] != title:
                continue
            document = documents.get(record["title"]) or next(
                (
                    item
                    for item in available_documents
                    if item.file.name.endswith(record["filename"])
                ),
                None,
            )
            resources.append(
                {
                    "title": record["title"],
                    "description": record["description"],
                    "document": document,
                    "external_url": (
                        ""
                        if document or not record.get("source_available", True)
                        else record["source_url"]
                    ),
                    "resource_type": (
                        "Presentation"
                        if record["filename"].endswith(".pptx")
                        else "PDF guide"
                        if title in {item[1] for item in METHODOLOGY_GROUPS}
                        else "PDF report"
                    ),
                }
            )
        groups.append(
            (
                "group",
                {
                    "anchor": anchor,
                    "title": title,
                    "description": description,
                    "icon": icon,
                    "resources": resources,
                },
            )
        )
    return groups


class Command(BaseCommand):
    help = "Create and populate the editable RCC Training function page."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync-resources",
            action="store_true",
            help="Refresh the two resource sections from the audited training library.",
        )

    def handle(self, *args, **options):
        parent = ServicePage.objects.filter(
            service__name__iexact=ServicePage.rcc_service_name,
        ).first()
        if not parent:
            self.stderr.write(
                "The Regional Climate Center service page was not found; "
                "page creation was deferred."
            )
            return

        page = RCCTrainingPage.objects.child_of(parent).first()
        if page:
            self.stdout.write(
                "RCC Training page already exists; its dashboard content was preserved."
            )
        else:
            ojt_page = OnTheJobTrainingPage.objects.live().first()
            page = RCCTrainingPage(
                title="Training",
                slug="training",
                banner_title="Strengthening climate-service capacity",
                banner_subtitle=(
                    "Methods, practical learning and regional knowledge exchange "
                    "for African climate-service providers."
                ),
                banner_image=parent.banner_image,
                introduction_title="From climate data to usable regional services",
                introduction_text=(
                    "<p>ACMAD develops and shares methods, tools and practical skills "
                    "for data services, climate monitoring, long-range forecasting "
                    "and climate projections.</p><p>Training combines guidance "
                    "documents, workshops, placements, e-learning and regional "
                    "Climate Outlook Forum activities.</p>"
                ),
                introduction_image=parent.introduction_image,
                focus_areas=[
                    ("area", {"title": "Climate data services", "description": "Quality control, rescue, management and preparation of climate observations."}),
                    ("area", {"title": "Climate monitoring", "description": "Indices, diagnostics and tools for assessing anomalies and extremes."}),
                    ("area", {"title": "Long-range forecasting", "description": "Objective seasonal prediction, model output and consensus outlook production."}),
                    ("area", {"title": "Climate projections", "description": "Interpretation and application of model output for climate-change information."}),
                ],
                programmes=[
                    ("programme", {"title": "On-the-job training and secondment", "description": "Structured placements at ACMAD for hands-on learning, mentoring and institutional exchange.", "icon": "user", "page": ojt_page, "external_url": "", "link_label": "View programme"}),
                    ("programme", {"title": "Product development and interpretation", "description": "Training on producing, interpreting and applying RCC monitoring and forecast products.", "icon": "tasks", "page": None, "external_url": "", "link_label": ""}),
                    ("programme", {"title": "Workshops, seminars and conferences", "description": "Regional learning events on African climate, RCC functions and climate-service practice.", "icon": "group", "page": None, "external_url": "", "link_label": ""}),
                    ("programme", {"title": "E-learning", "description": "Learning themes include data rescue and management, climate prediction, model output, monitoring and long-range forecasting.", "icon": "desktop", "page": None, "external_url": "", "link_label": ""}),
                    ("programme", {"title": "MEDCOF seasonal objective forecasting", "description": "Training materials developed for objective seasonal forecasting through the Mediterranean Climate Outlook Forum.", "icon": "globe", "page": None, "external_url": "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/PROJECTS/CLIMSA/CDD/ACTIVITIES/SERVICES/Climate_outlook_forum/MEDCOF/Medcof_training_on_Seas_Objec_Fcst/catalog.html", "link_label": "Open training archive"}),
                    ("programme", {"title": "Surveys and training-needs analysis", "description": "Questionnaires, analysis reports and proposals used to shape relevant regional capacity development.", "icon": "form", "page": None, "external_url": "", "link_label": ""}),
                ],
                methodology_groups=resource_groups(METHODOLOGY_GROUPS),
                report_groups=resource_groups(REPORT_GROUPS),
                training_videos=[
                    ("video", {"title": "Seasonal Forecasts Explained: Introduction", "description": "An introduction to seasonal forecasting and the information it provides.", "youtube_id": "CucEP23gWfU", "video_url": "https://www.youtube.com/watch?v=CucEP23gWfU"}),
                    ("video", {"title": "How seasonal forecasts are produced", "description": "The principal stages involved in generating a seasonal forecast.", "youtube_id": "1B4DjkmbBZ8", "video_url": "https://www.youtube.com/watch?v=1B4DjkmbBZ8"}),
                    ("video", {"title": "Interpreting seasonal forecast output", "description": "How to read probabilities and understand seasonal forecast information.", "youtube_id": "R3DE3A0boMs", "video_url": "https://www.youtube.com/watch?v=R3DE3A0boMs"}),
                    ("video", {"title": "Forecast delivery and climate services", "description": "Communicating seasonal information and connecting forecasts with user decisions.", "youtube_id": "QJ7VuqaU8dg", "video_url": "https://www.youtube.com/watch?v=QJ7VuqaU8dg"}),
                ],
                closing_text=(
                    "<p>National Meteorological and Hydrological Services and "
                    "regional partners can contact ACMAD to discuss training needs, "
                    "technical cooperation and future learning activities.</p>"
                ),
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(f"Created RCC Training page at {page.url}")
            )

        if options["sync_resources"]:
            page.methodology_groups = resource_groups(METHODOLOGY_GROUPS)
            page.report_groups = resource_groups(REPORT_GROUPS)
            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Refreshed RCC Training resources."))

        self._link_custom_menu(page)

    def _link_custom_menu(self, page):
        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            return
        navigation = NavigationSettings.for_site(site)
        menu = []
        changed = False
        for block in navigation.rcc_main_menu:
            value = dict(block.value)
            if value.get("label", "").strip().casefold() == "training":
                if value.get("page") != page or value.get("external_url"):
                    value["page"] = page
                    value["external_url"] = ""
                    changed = True
            menu.append((block.block_type, value))
        if changed:
            navigation.rcc_main_menu = menu
            navigation.save()
            self.stdout.write(
                self.style.SUCCESS("Linked the custom RCC Training menu item.")
            )
