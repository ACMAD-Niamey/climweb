from django.core.management.base import BaseCommand
from wagtail.models import Page

from climweb.pages.services.models import OnTheJobTrainingPage, ServicePage


MODULES = [
    ("Numerical Weather Prediction", "Access, visualise, interpret and evaluate NWP and climate-model outputs for operational forecasting and early warning."),
    ("Climate Change Projections for Risk Assessment", "Process CMIP and CORDEX datasets, develop scenarios and support vulnerability, risk and adaptation assessments."),
    ("Climate Data Rescue and Management", "Quality-control, homogenise, archive and manage climate data with tools such as CLIMSOFT."),
    ("Climate Monitoring and Prediction", "Use global climate data, monitoring tools and ensemble techniques for seasonal and subseasonal forecasts."),
    ("EUMETSAT Data for Weather Watch and Early Warning", "Use satellite, radar and NWP products to track severe weather and issue timely warnings."),
    ("Impact-Based Forecasting", "Combine hazard, exposure and vulnerability information to produce actionable sector-specific forecasts."),
    ("Downscaling Weather Forecasts with WRF", "Build Linux, networking and WRF skills for high-resolution local forecasting."),
    ("Climate and Weather Data Analysis", "Apply statistical and computational methods to large, high-resolution datasets and products."),
    ("Artificial Intelligence", "Apply foundational AI techniques to forecasting, climate monitoring and data workflows."),
    ("Climate Services for Health", "Map and forecast climate-sensitive disease risks using historical and real-time information."),
    ("Climate Software and Interface Administration", "Install, operate and maintain stations, PUMA systems, networks and high-performance computing."),
    ("Climate Finance and Project Management", "Understand climate-finance institutions and develop fundable climate project proposals."),
    ("Climate Services Communication and Weather Presentation", "Translate science into accessible information for television, digital media and public decision support."),
]

APPLICATION_STEPS = [
    (
        "Request through PR or your NMHS",
        "<p>Begin with an official request through the appropriate Permanent Representative (PR) or National Meteorological and Hydrological Service.</p>",
    ),
    (
        "Complete the training project",
        "<p>Define the proposed training project and submit the nomination letter, CV, diplomas or certificates, and motivation letter requested by ACMAD.</p>",
    ),
    (
        "Sign the convention",
        "<p>After selection, ACMAD and the nominating institution agree and sign the training convention before travel and logistical arrangements are confirmed.</p>",
    ),
]

TESTIMONIALS = [
    (
        "Miroirdine Kamardine",
        "NMHS Comoros",
        "This training provided essential skills in impact-focused seasonal forecasting. The expertise gained at ACMAD will improve anticipation and response to climate challenges, helping mitigate economic losses and support food security in the Union of the Comoros.",
    ),
    (
        "Esther Modi",
        "NMHS Cameroon",
        "The combined training in weather prediction and communication sharpened my forecasting skills for extreme events and taught me to turn science into actionable, user-friendly information.",
    ),
]


class Command(BaseCommand):
    help = "Create the editable On-the-Job Training and Secondment Programme page."

    def handle(self, *args, **options):
        parent = ServicePage.objects.filter(slug="capacity-building").first()
        if not parent:
            self.stderr.write("Capacity Development service page was not found; training page creation was deferred.")
            return

        existing = Page.objects.child_of(parent).filter(slug="on-the-job-training").first()
        if existing:
            if isinstance(existing.specific, OnTheJobTrainingPage):
                self.stdout.write("On-the-Job Training page already exists; dashboard content was preserved.")
            else:
                self.stderr.write("The existing on-the-job-training child is a different page type and was left unchanged.")
            return

        page = OnTheJobTrainingPage(
            title="On-the-Job Training and Secondment Programme",
            slug="on-the-job-training",
            banner_title="Build operational expertise for a changing climate",
            banner_subtitle="On-the-Job Training and Secondment Programme",
            banner_image=parent.banner_image,
            introduction_title="Building a skilled African meteorological workforce",
            introduction_text=(
                "<p>ACMAD's programme strengthens African meteorological experts in advanced operational methods and tools, "
                "scaling effective climate services from regional to national level through practical case studies and professional exchange.</p>"
            ),
            introduction_image=parent.introduction_image,
            objectives=(
                "<p>The programme strengthens NMHS capacity for accurate weather and climate services by advancing forecasting, data management, "
                "early-warning and AI skills; supporting ACMAD-NMHS product co-production; and building a continent-wide practitioner network.</p>"
            ),
            eligibility=(
                "<p><strong>On-the-Job Training:</strong> junior to mid-career NMHS professionals.</p>"
                "<p><strong>Secondment:</strong> mid-career NMHS professionals and experts involved in WMO programmes.</p>"
            ),
            duration="On-the-Job Training: 2-6 months · Secondment: 1-12 months",
            location="ACMAD Headquarters, Niamey, Niger",
            languages="English and French",
            benefits=(
                "<ul><li>Round-trip ticket and allowance</li><li>Hands-on operational training</li>"
                "<li>Certificate upon completion</li><li>Membership in ACMAD's focal-point network</li></ul>"
            ),
            training_modules=[("module", {"title": title, "description": description}) for title, description in MODULES],
            application_introduction=(
                "<p>Applications are coordinated through national services. Selection considers regional balance, gender equity and alignment with national priorities.</p>"
            ),
            application_steps=[("step", {"title": title, "description": description}) for title, description in APPLICATION_STEPS],
            application_email="secretariat@acmad.org",
            reports_introduction="<p>Download reports prepared by visiting experts at the end of their placement.</p>",
            visitor_reports=[],
            testimonials=[
                ("testimony", {"name": name, "organisation": organisation, "quote": quote})
                for name, organisation, quote in TESTIMONIALS
            ],
            gallery=[],
            accommodation_introduction=(
                "<p>Participants are hosted in Niamey. Current recommended accommodation, rates and contact information can be maintained here by the programme team.</p>"
            ),
            accommodation_options=[],
        )
        parent.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f"Created On-the-Job Training page at {page.url}"))
