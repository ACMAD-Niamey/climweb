from django.core.management.base import BaseCommand

from climweb.pages.data_request.models import DataRequestPage
from climweb.pages.services.models import RCCDataServicesPage, ServicePage


VERIFIED_ON = "2026-09-08"


def dataset(
    title,
    description,
    access_type,
    *,
    url="",
    local_dataset_key="",
    coverage="",
    formats="",
    source="",
):
    return {
        "title": title,
        "description": description,
        "access_type": access_type,
        "access_url": url,
        "local_dataset_key": local_dataset_key,
        "coverage": coverage,
        "formats": formats,
        "source": source,
        "last_verified": VERIFIED_ON if url else None,
    }


CLIMATE_INDICES_DATASET = dataset(
    "Climate indices and historical graphs",
    "Preserved rainfall and temperature anomaly, trend, scenario and ranking figures from the legacy RCC collection.",
    "archive",
    local_dataset_key="climate-indices",
    coverage="Central Africa studies and Africa-wide analyses",
    formats="PNG historical figures",
    source="ACMAD RCC",
)

CLIMSOFT_RESOURCES_DATASET = dataset(
    "Climsoft resources and documentation",
    "Locally preserved manuals for Climsoft installation, administration, development, routine use, data entry and climate-index analysis.",
    "archive",
    local_dataset_key="climsoft-resources",
    coverage="Technical and operational guidance",
    formats="PDF and PowerPoint",
    source="ACMAD RCC",
)

RDT_DATASET = dataset(
    "Rapidly Developing Thunderstorm data",
    "Locally preserved RDT imagery and operational products for convective-storm monitoring.",
    "archive",
    local_dataset_key="thunderstorm-nowcasting",
    coverage="Africa",
    formats="Satellite imagery and product archive",
    source="ACMAD RCC",
)

ITD_DATASET = dataset(
    "Intertropical Discontinuity monitoring",
    "Locally preserved ITD and ITCZ monitoring maps and operational products.",
    "archive",
    local_dataset_key="itd-itcz",
    coverage="Africa",
    formats="PDF and image archive",
    source="ACMAD RCC",
)


DATA_GROUPS = [
    (
        "group",
        {
            "anchor": "observations",
            "title": "Observations and station data",
            "summary": "Quality-controlled station observations and rainfall estimates supporting monitoring, verification and national climate services.",
            "icon": "map-marker-alt",
            "datasets": [
                dataset(
                    "ARC2 estimated daily station rainfall",
                    "Daily ARC2 precipitation estimates organized for African synoptic stations.",
                    "open",
                    url="http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/climatedataservice/Synoptic_Daily_ARC2_Data/catalog.html",
                    local_dataset_key="arc2",
                    coverage="African synoptic stations",
                    formats="THREDDS catalogue",
                    source="ACMAD SGBD",
                ),
                dataset(
                    "CPC-Unified estimated daily rainfall",
                    "Daily CPC-Unified precipitation estimates prepared for station-level assessment.",
                    "open",
                    url="http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/climatedataservice/Synoptic_Daily_CPC_Unified_Data/catalog.html",
                    local_dataset_key="cpc-unified",
                    coverage="African synoptic stations",
                    formats="THREDDS catalogue",
                    source="ACMAD SGBD",
                ),
                dataset(
                    "Quality-controlled country station records",
                    "Minimum, maximum and mean temperature, precipitation and associated station records maintained through Climsoft.",
                    "request",
                    coverage="By country and station",
                    formats="Climsoft export",
                    source="ACMAD and NMHSs",
                ),
            ],
        },
    ),
    (
        "group",
        {
            "anchor": "gridded-data",
            "title": "Gridded climate data",
            "summary": "Continental precipitation and temperature fields for monitoring anomalies, rainfall frequency and seasonal conditions.",
            "icon": "layer-group",
            "datasets": [
                dataset(
                    "Monthly and seasonal precipitation",
                    "CPC CAMS-OPI precipitation fields served through the IRI Data Library.",
                    "external",
                    url="https://iridl.ldeo.columbia.edu/expert/SOURCES/.NOAA/.NCEP/.CPC/.CAMS_OPI/.v0208/.mean/.prcp",
                    coverage="Africa and global domains",
                    formats="IRI Data Library",
                    source="NOAA CPC / IRI",
                ),
                dataset(
                    "Dekadal ARC2 precipitation",
                    "Daily ARC2 estimates suitable for dekadal rainfall aggregation and monitoring.",
                    "external",
                    url="https://iridl.ldeo.columbia.edu/expert/SOURCES/.NOAA/.NCEP/.CPC/.FEWS/.Africa/.DAILY/.ARC2/.daily/.est_prcp/",
                    coverage="Africa",
                    formats="IRI Data Library",
                    source="NOAA CPC / IRI",
                ),
                dataset(
                    "Seasonal rainfall climatology maps",
                    "Archived seasonal mean precipitation and rainy-day frequency maps for standard three-month periods.",
                    "archive",
                    url="http://sgbd.acmad.org:8080/thredds/fileServer/ACMAD/CDD/statisticalanalysis/Precipitation/Gridded_Observation/01_JFM_Afr.png/",
                    local_dataset_key="seasonal-maps",
                    coverage="Africa",
                    formats="PNG map archive",
                    source="ACMAD SGBD",
                ),
                CLIMATE_INDICES_DATASET,
            ],
        },
    ),
    (
        "group",
        {
            "anchor": "models",
            "title": "Climate models and projections",
            "summary": "Regional simulation, downscaling and CORDEX archives used for climate-change analysis and impact assessment.",
            "icon": "globe",
            "datasets": [
                dataset(
                    "EIN15 regional model output",
                    "Archived regional climate simulation files available from the local RCC collection.",
                    "archive",
                    url="http://sgbd.acmad.org:8080/thredds/catalog/ein15output/catalog.html",
                    local_dataset_key="ein15",
                    coverage="Africa",
                    formats="NetCDF",
                    source="ACMAD SGBD",
                ),
                dataset(
                    "CORDEX NOAA-GFDL GFDL-ESM2M",
                    "Regional downscaling archive based on the NOAA-GFDL GFDL-ESM2M global climate model.",
                    "archive",
                    url="http://sgbd.acmad.org:8080/thredds/catalog/cordex/NOAA-GFDL-GFDL-ESM2M/catalog.html",
                    coverage="CORDEX Africa domain",
                    formats="THREDDS catalogue",
                    source="CORDEX / ACMAD",
                ),
                dataset(
                    "Tailored regional model extracts",
                    "Subset, period and variable requests for impact studies and national adaptation planning.",
                    "request",
                    coverage="Defined in each request",
                    formats="NetCDF or agreed format",
                    source="ACMAD",
                ),
            ],
        },
    ),
    (
        "group",
        {
            "anchor": "tools-guidance",
            "title": "Operational tools and guidance",
            "summary": "Monitoring interfaces, climate-data management guidance and technical manuals supporting operational use.",
            "icon": "cogs",
            "datasets": [
                RDT_DATASET,
                ITD_DATASET,
                CLIMSOFT_RESOURCES_DATASET,
            ],
        },
    ),
]


class Command(BaseCommand):
    help = "Create the editable RCC Data Services catalogue page."

    def handle(self, *args, **options):
        parent = ServicePage.objects.filter(
            service__name__iexact=ServicePage.rcc_service_name,
        ).first()
        if not parent:
            self.stderr.write("The Regional Climate Center service page was not found; page creation was deferred.")
            return

        existing = RCCDataServicesPage.objects.filter(slug="data-services").first()
        if existing:
            groups = []
            changed = False
            for block in existing.data_groups:
                group = dict(block.value)
                datasets = []
                for item in block.value["datasets"]:
                    entry = dict(item)
                    if entry.get("title") == "RClimDex user manual":
                        changed = True
                        continue
                    if entry.get("title") == "Climsoft administrator guide":
                        entry = dict(CLIMSOFT_RESOURCES_DATASET)
                        changed = True
                    local_keys = {
                        "ARC2 estimated daily station rainfall": "arc2",
                        "CPC-Unified estimated daily rainfall": "cpc-unified",
                        "Seasonal rainfall climatology maps": "seasonal-maps",
                        "Climate indices and historical graphs": "climate-indices",
                        "EIN15 regional model output": "ein15",
                        "Climsoft resources and documentation": "climsoft-resources",
                        "Rapidly Developing Thunderstorm data": "thunderstorm-nowcasting",
                        "Intertropical Discontinuity monitoring": "itd-itcz",
                    }
                    local_key = local_keys.get(entry.get("title"))
                    if local_key and entry.get("local_dataset_key") != local_key:
                        entry["local_dataset_key"] = local_key
                        changed = True
                    if entry.get("title") == "EIN15 regional model output":
                        if entry.get("description") == "Archived regional climate simulation output distributed through the ACMAD THREDDS server.":
                            entry["description"] = "Archived regional climate simulation files available from the local RCC collection."
                            changed = True
                        if entry.get("formats") == "THREDDS catalogue":
                            entry["formats"] = "NetCDF"
                            changed = True
                    local_product_datasets = {
                        RDT_DATASET["title"]: RDT_DATASET,
                        ITD_DATASET["title"]: ITD_DATASET,
                    }
                    replacement = local_product_datasets.get(entry.get("title"))
                    if replacement:
                        for field in (
                            "description",
                            "access_type",
                            "access_url",
                            "coverage",
                            "formats",
                            "source",
                            "last_verified",
                        ):
                            if entry.get(field) != replacement[field]:
                                entry[field] = replacement[field]
                                changed = True
                    datasets.append(entry)
                if group.get("anchor") == "gridded-data" and not any(
                    item.get("title") == CLIMATE_INDICES_DATASET["title"] for item in datasets
                ):
                    datasets.append(dict(CLIMATE_INDICES_DATASET))
                    changed = True
                if group.get("anchor") == "tools-guidance" and not any(
                    item.get("title") == CLIMSOFT_RESOURCES_DATASET["title"] for item in datasets
                ):
                    datasets.append(dict(CLIMSOFT_RESOURCES_DATASET))
                    changed = True
                group["datasets"] = datasets
                groups.append(("group", group))
            if changed:
                existing.data_groups = groups
                existing.save_revision().publish()
                self.stdout.write(self.style.SUCCESS("Linked RCC catalogue entries to local collections."))
            else:
                self.stdout.write("RCC Data Services page already exists; dashboard content was preserved.")
            return

        data_request_page = DataRequestPage.objects.live().first()
        page = RCCDataServicesPage(
            title="Data Services",
            slug="data-services",
            banner_title="Climate data for Africa",
            banner_subtitle="Discover observations, gridded datasets, model archives and technical resources provided through ACMAD and its partners.",
            banner_image=parent.banner_image,
            introduction_title="One catalogue for regional climate data",
            introduction_text=(
                "<p>Explore operational and historical climate datasets used for monitoring, forecasting, research and risk assessment. "
                "Each entry states how it can be accessed and when its endpoint was last verified.</p>"
            ),
            introduction_image=parent.introduction_image,
            catalogue_notice=(
                "<p><strong>Access and freshness vary by source.</strong> Open links have been checked, external services may require an account, "
                "and restricted station records are supplied only after review by ACMAD and the relevant data owner.</p>"
            ),
            data_groups=DATA_GROUPS,
            data_request_page=data_request_page,
        )
        parent.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f"Created RCC Data Services page at {page.url}"))
