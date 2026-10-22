"""Regional Climate Outlook Forum content used by the RCC public pages."""

from django.utils.translation import gettext_lazy as _


# Exact background descriptions retained from the corresponding legacy RCC pages.
# SARCOF and GHACOF did not have equivalent profile pages on the legacy ACMAD site,
# so their locally authored summaries remain the fallback.
LEGACY_FORUM_BACKGROUNDS = {
    "ACCOF": (
        "<p>The World Meteorological Organization has established a three-tiered "
        "approach for seasonal climate prediction with Global, Regional and National "
        "institutions supporting production and delivery of climate outlooks. In "
        "Africa, continental, regional and national climate centres are operating "
        "leading to the need for harmonization, consistency in processes and products "
        "as well as coordination among stakeholders.</p>"
        "<p>The African Centre for Meteorological Applications and Development "
        "(ACMAD) as a World Meteorological Organization (WMO) Regional Climate Centre "
        "(RCC) for Africa in partnership with African Union Commission (AUC) and "
        "partners organizes the Africa Continental Climate Outlook Forum (ACCOF) "
        "currently on a monthly basis as part of its Regional Climate Centre (RCC)’s "
        "coordination function for africa.</p>"
        "<p>This action seeks to build capacity on latest climate forecasting science "
        "and technology, harmonize climate outlook generation and delivery methods "
        "tools, products and ensure consistency in climate outlook statements delivered "
        "across the continent.</p>"
    ),
    "PRESAO": (
        "<p>This region typically covers the area between the Sahara desert in the "
        "north and the tropical Atlantic coast to the south. The regional climate is "
        "dominated by the West African monsoon during the rainy season typically "
        "occurring during northern hemisphere summer (from July to September).</p>"
        "<p>Major sources of seasonal climate variability and predictability in the "
        "region include Sea Surface Temperatures (SSTs) of the equatorial Pacific "
        "(ENSO region), the Mediterranean Sea, the tropical Atlantic Ocean (North and "
        "South) as well as the Western Equatorial Indian Ocean. SST predictive skill "
        "is limited over most ocean basins except the ENSO region. It is recognized "
        "that soil moisture is another important source of climate variability and "
        "predictability over the region.</p>"
        "<p>Uncertainties on SST forecasts over the Mediterranean Sea, the tropical "
        "Atlantic and equatorial Indian Ocean, soil moisture forecasts over land areas "
        "of the region are documented.</p>"
        "<p>Improvement of ocean models over the tropical Atlantic, land surface models "
        "over sub-Saharan Africa and coupled ocean-atmosphere-land models are required "
        "to provide better inputs to operational seasonal prediction for the region.</p>"
        "<p>Floods and droughts, late onsets, early and late cessation of rains, dry and "
        "wet spells are the main climate hazards of the region. Shortage of water, "
        "multiple sowing, food insecurity due to reduction in crop yields, conflicts "
        "between farmers and herders due to droughts, epidemic malaria regularly occur. "
        "Roads and other infrastructure damages, loss of lives and properties associated "
        "with floods have become a matter of strong concern in many cities of the area "
        "since the late 90s.</p>"
    ),
    "PRESASS": (
        "<p>This region typically covers the area between the Sahara desert in the "
        "north and the tropical Atlantic coast to the south. The regional climate is "
        "dominated by the West African monsoon during the rainy season typically "
        "occurring during northern hemisphere summer (from July to September).</p>"
        "<p>Major sources of seasonal climate variability and predictability in the "
        "region include Sea Surface Temperatures (SSTs) of the equatorial Pacific "
        "(ENSO region), the Mediterranean Sea, the tropical Atlantic Ocean (North and "
        "South) as well as the Western Equatorial Indian Ocean. SST predictive skill "
        "is limited over most ocean basins except the ENSO region. It is recognized "
        "that soil moisture is another important source of climate variability and "
        "predictability over the region.</p>"
        "<p>Uncertainties on SST forecasts over the Mediterranean Sea, the tropical "
        "Atlantic and equatorial Indian Ocean, soil moisture forecasts over land areas "
        "of the region are documented.</p>"
        "<p>Improvement of ocean models over the tropical Atlantic, land surface models "
        "over sub-Saharan Africa and coupled ocean-atmosphere-land models are required "
        "to provide better inputs to operational seasonal prediction for the region.</p>"
        "<p>Floods and droughts, late onsets, early and late cessation of rains, dry and "
        "wet spells are the main climate hazards of the region. Shortage of water, "
        "multiple sowing, food insecurity due to reduction in crop yields, conflicts "
        "between farmers and herders due to droughts, epidemic malaria regularly occur. "
        "Roads and other infrastructure damages, loss of lives and properties associated "
        "with floods have become a matter of strong concern in many cities of the area "
        "since the late 90s.</p>"
    ),
    "PRESAC": (
        "<p>This region typically covers the equatorial region of Africa including "
        "Cameroon, Central Africa Republic, Gabon, Congo, Democratic Republic of Congo, "
        "Equatorial Guinea, Sao Tome and Principe and Burundi. The regional climate is "
        "dominated by convective activity and precipitation in the InterTropical "
        "Convergence Zone (ITCZ) with October-November-December as the main target "
        "season.</p>"
        "<p>Major sources of seasonal climate variability and predictability in the "
        "region include Sea Surface Temperatures (SSTs) of the equatorial Pacific "
        "(ENSO region), tropical northern and southern Atlantic and equatorial western "
        "Indian Oceans. Uncertainties on SST forecasts over tropical Atlantic and the "
        "equatorial Indian Ocean as well as limitations on the representation of "
        "interactions between the Congo Basin, the regional and global atmosphere are "
        "not well documented.</p>"
        "<p>Improvement of ocean models over the tropical Atlantic, land surface models "
        "over sub-Saharan Africa and coupled ocean-atmosphere-land models are required "
        "to provide better inputs to operational seasonal prediction for the region.</p>"
        "<p>Improvement of understanding and representation of processes and interactions "
        "in models are required to provide better inputs to operational seasonal "
        "prediction for the region.</p>"
        "<p>Floods, dry and wet spells, anomalous onset and cessation of rains are the "
        "main climate hazards of the region. Water borne diseases, roads and other "
        "infrastructure damages, loss of lives and properties are associated with heavy "
        "precipitation, strong winds and floods. Losses in food production (up to 30%) "
        "due to heavy rains occurring during havesting period increasing humidity "
        "leading to losses or damages in crops are noted over the area.</p>"
    ),
    "PRESAGG": (
        "<p>This region typically covers the Coastal Atlantic region of West and "
        "Central Africa including Guinea-Conakry, Liberia, Sierra-Leone, Côte d’Ivoire, "
        "Ghana, Nigeria, Togo, Benin, Cameroon and Equatorial Guinea. The regional "
        "climate is dominated by the InterTropical Convergence Zone (ITCZ) and the "
        "African monsoon with March-April-May as the main target season.</p>"
        "<p>Major sources of seasonal climate variability and predictability in the "
        "region include Sea Surface Temperatures (SSTs) of the equatorial Pacific "
        "(ENSO region), tropical northern and southern Atlantic as well as the "
        "Equatorial Atlantic. Uncertainties on SST forecasts over the equatorial and "
        "tropical Atlantic, understanding and prediction of processes and phenomena "
        "embedded in the ITCZ and the African monsoon during the target season are not "
        "well documented.</p>"
        "<p>Improvement of understanding and representation of processes and interactions "
        "in models are required to provide better inputs to operational seasonal "
        "prediction for the region.</p>"
        "<p>Dry and wet spells, strong winds and heavy rains, anomalous onset of the "
        "rains are the main climate hazards of the region. Disruptions on the planting "
        "periods, damages to infrastructure (eg. roads, electricity distribution "
        "systems,…) due to heavy rains and storms are noted over the area.</p>"
    ),
    "MEDCOF": (
        "<p>This region typically covers the Mediterranean area in Africa between the "
        "Mediteranean Sea and Sub Saharan Africa. The regional climate is hot in summer "
        "and wet winter. The regional climate is mainly dominated by winter and summer "
        "regimes.</p>"
        "<p>Large scale circulation in the mid latitude exerts a strong influence on "
        "winter precipitation trough the North atlantic Oscillation(NAO). ENSO, shifts "
        "in the upper troposphere jet over Eastern mediteranean region, synoptic systems "
        "passing over central and northern Europe and Scandinavian pattern are additional "
        "features impacting Mediterranean winter climate. In summer, Asian and African "
        "monsoons, blockings, mediteranean SSTs significantly modulate mediteranean "
        "climate.</p>"
        "<p>Major sources of seasonal climate variability and predictability in the "
        "region include Sea Surface Temperatures (SSTs) of the equatorial Pacific "
        "(ENSO region), the Tropical North Atlantic SSTs, Eurasian snow cover, "
        "Scandinavian pattern, the North Atlantic Oscillation, the Quasi Biennal "
        "Oscillation, Tropical intrusion, troughs, ridges and blockings.</p>"
        "<p>It is recognized that soil moisture is another important source of local "
        "climate variability and predictability over the region. Uncertainties on SST "
        "forecasts over the tropical north Atlantic, the NAO and soil moisture forecasts "
        "over the region are documented.</p>"
        "<p>Improvement of ocean models over the tropical north Atlantic, representation "
        "of stratosphere-troposphere interactions in climate models, land surface models "
        "over the Mediterranean region, and coupled ocean-atmosphere-land models are "
        "required to provide better inputs to operational seasonal prediction for the "
        "region.</p>"
        "<p>Floods and droughts, summer heat and cold waves, abnormal onsets are the main "
        "climate hazards of the region. Shortages of water, reduction in food production "
        "due to droughts occur. Roads and other infrastructure damages, loss of lives and "
        "properties are associated with floods have become a matter of strong concern in "
        "cities of the area.</p>"
    ),
    "SWIOCOF": (
        "<p>The Regional Climate Outlook Forums (RCOFs) have been operational in many "
        "parts of the world with the aim to develop and provide consensus-based climate "
        "outlooks and related impacts, preparedness and response information on a "
        "regional scale. These activities support decision making to manage "
        "climate-related risks and support sustainable development.</p>"
        "<p>This process was initiated by WMO’s Climate Information and Prediction "
        "Services (CLIPS) project, in collaboration with National Meteorological and "
        "Hydrological Services (NMHSs), regional/international climate centres among "
        "many other partners. RCOFs have been recognized to be prominent among the key "
        "regional mechanisms to support the implementation of the Global Framework for "
        "Climate Services (GFCS), Sendai Framework for Disaster Risk Reduction and "
        "Sustainable Development Goals.</p>"
        "<p>IOC members share common geographical and climatic features such as small "
        "Islands (except Madagascar), sharp topography, maritime influence, tropical "
        "extreme weather events such as torrential rainfall or cyclones, and a similar "
        "seasonal cycle typical of the Southern Hemisphere. Due to these geographical "
        "and climactic similarities, the IOC members also share a number of concerns and "
        "issues in terms of vulnerability to climate variability and climate change.</p>"
        "<p>Understanding regional and local climate including teleconnections with "
        "large-scale variability, assessing predictability and facilitating tailoring "
        "and application of climate information are among the challenges facing the "
        "region.</p>"
        "<p>The idea of a regional forum for jointly developing seasonal climate outlooks "
        "dedicated to the countries of the South-West Indian Ocean is not new. The "
        "interest and feasibility of such a forum was a regular topic for discussion in "
        "the regional workshops organized within ACCLIMATE project on the adaptation of "
        "IOC countries to climate change: www.acclimateoi.net.</p>"
        "<p>The workshop held in Saint-Denis de La Réunion at Météo-France (27-30 "
        "September 2011) in the framework of ACCLIMATE project led to the organization "
        "of a first South-West Indian Ocean Climate Outlook Forum (SWIOCOF) in September "
        "2012. In the absence of sustained financial support and clear governance, "
        "SWIOCOFs could not be regularly organized, although it was unanimously agreed "
        "that SWIOCOF was of great benefit to the South-West Indian Ocean countries/"
        "territories.</p>"
        "<p>In parallel, in June 2012, the African Center of Meteorological Application "
        "for Development (ACMAD) held in Moroni, Comoros, a “scoping workshop on seasonal "
        "forecasting of cyclone activity in the South-West Indian Ocean region, for "
        "climate risk management and adaptation to climate change for sustainable "
        "development”. This workshop was followed by two RCOFs in October 2013 and "
        "January 2016.</p>"
        "<p>In addition, two longstanding RCOFs, namely the Southern African Climate "
        "Outlook Forum (SARCOF) and the Greater Horn of Africa Climate Outlook Forum "
        "(GHACOF) also extend their scope to conditions in the adjoining Indian Ocean, "
        "though their main focus is on the continental climate.</p>"
        "<p>However, participants representing the SouthWest Indian Ocean countries/"
        "territories in these forums have indicated that, due to the geographic and "
        "climatic specificities of the South-West Indian Ocean region, the applicability "
        "of forums targeted at the broader sub-regions is limited.</p>"
    ),
}


CONSENSUS_FORUMS = (
    {
        "slug": "accof",
        "code": "ACCOF",
        "name": _("African Continental Climate Outlook Forum"),
        "region": _("Africa"),
        "season": _("Continental outlooks and cross-regional synthesis"),
        "summary": _(
            "A continental forum that consolidates regional evidence and expert "
            "judgement into a shared climate outlook for Africa."
        ),
        "overview": _(
            "ACCOF brings together Regional Climate Centres, National "
            "Meteorological and Hydrological Services, global producing centres "
            "and users to interpret climate drivers and agree on a continental "
            "seasonal outlook."
        ),
        "coverage": _("All African sub-regions, with input from the regional outlook forums."),
        "drivers": _(
            "Large-scale ocean and atmosphere conditions, regional circulation "
            "features, land-surface conditions and guidance from global and "
            "regional ensemble systems."
        ),
        "hazards": _(
            "Drought, flood, heat and other seasonal anomalies with potential "
            "impacts across climate-sensitive sectors."
        ),
        "users": _(
            "Continental and regional institutions, NMHSs, disaster-risk agencies, "
            "water, agriculture, health, energy and humanitarian partners."
        ),
        "priorities": _(
            "Strengthen the connection between sub-regional outlooks, impact-based "
            "information and consistent communication across the continent."
        ),
        "document_codes": ("ACCOF",),
    },
    {
        "slug": "presao",
        "code": "PRESAO",
        "name": _("Seasonal Outlook Forum for West Africa, Chad and Cameroon"),
        "region": _("West Africa, Chad and Cameroon"),
        "season": _("Primarily July–August–September"),
        "summary": _(
            "Consensus seasonal guidance for countries influenced by the West "
            "African monsoon."
        ),
        "overview": _(
            "The forum assesses the expected rainy season across the zone between "
            "the Sahara and the tropical Atlantic coast. It combines model output, "
            "historical evidence and national expertise to produce a common outlook."
        ),
        "coverage": _(
            "Mauritania, Senegal, Mali, Guinea-Bissau, Guinea, Côte d’Ivoire, "
            "Burkina Faso, Niger, Chad, Cameroon, Central African Republic, Nigeria, "
            "Benin, Togo, Ghana, Liberia and Cabo Verde."
        ),
        "drivers": _(
            "ENSO and sea-surface temperatures in the tropical Atlantic, "
            "Mediterranean and western equatorial Indian Ocean, together with land "
            "and soil-moisture conditions."
        ),
        "hazards": _(
            "Floods, drought, delayed onset or early cessation, prolonged dry spells "
            "and periods of intense rainfall."
        ),
        "users": _(
            "Agriculture, water, health, disaster management and media communities "
            "participate in interpreting impacts and developing recommendations."
        ),
        "priorities": _(
            "Increase forecast lead time, improve regional ocean–land–atmosphere "
            "modelling and expand subseasonal guidance for onset, cessation and spells."
        ),
        "document_codes": ("PRESAO",),
    },
    {
        "slug": "presass",
        "code": "PRESASS",
        "name": _("Seasonal Outlook Forum for the Sudano-Sahelian Region"),
        "region": _("Sudano-Sahelian West Africa"),
        "season": _("June–September rainy season"),
        "summary": _(
            "Rainfall, onset, cessation and dry-spell outlooks for the Sahelian and "
            "Sudanian zones."
        ),
        "overview": _(
            "PRESASS develops a shared outlook for the main West African rainy "
            "season, combining global and regional forecasts with monitoring, "
            "analogue years and expertise from participating countries."
        ),
        "coverage": _(
            "The Sahelian and Sudanian zones of West Africa, including Chad and the "
            "northern parts of Gulf of Guinea countries."
        ),
        "drivers": _(
            "West African monsoon circulation, ENSO, tropical Atlantic conditions, "
            "Mediterranean and Indian Ocean influences and land-surface feedbacks."
        ),
        "hazards": _(
            "Seasonal rainfall deficits or excess, flood risk, false starts, late "
            "onset, early cessation and long dry spells."
        ),
        "users": _(
            "NMHSs and regional organisations work with agriculture, food security, "
            "water, disaster-risk and humanitarian users."
        ),
        "priorities": _(
            "Translate the consensus outlook into national and sector-specific "
            "information while improving forecast verification and user feedback."
        ),
        "document_codes": ("PRESASS",),
    },
    {
        "slug": "presac",
        "code": "PRESAC",
        "name": _("Seasonal Outlook Forum for Central Africa"),
        "region": _("Central Africa"),
        "season": _("Primarily October–November–December"),
        "summary": _(
            "A regional consensus outlook focused on rainfall and related hazards "
            "across the Congo Basin and neighbouring countries."
        ),
        "overview": _(
            "PRESAC examines forecasts for the equatorial climate of Central Africa, "
            "where rainfall is closely related to convection and the movement of the "
            "Intertropical Convergence Zone."
        ),
        "coverage": _(
            "Cameroon, Central African Republic, Gabon, Republic of the Congo, "
            "Democratic Republic of the Congo, Equatorial Guinea, São Tomé and "
            "Príncipe and Burundi."
        ),
        "drivers": _(
            "ENSO, tropical Atlantic and western equatorial Indian Ocean conditions, "
            "and interactions between the Congo Basin and regional circulation."
        ),
        "hazards": _(
            "Floods, strong winds, anomalous onset or cessation, and damaging wet or "
            "dry spells."
        ),
        "users": _(
            "Water, agriculture, disaster management, infrastructure, health and "
            "media stakeholders contribute to impact interpretation."
        ),
        "priorities": _(
            "Improve understanding of Congo Basin land–atmosphere interactions and "
            "provide earlier outlooks, discharge guidance and heavy-rain vigilance."
        ),
        "document_codes": ("PRESAC",),
    },
    {
        "slug": "presagg",
        "code": "PRESAGG",
        "name": _("Seasonal Outlook Forum for Gulf of Guinea Countries"),
        "region": _("Gulf of Guinea"),
        "season": _("Primarily March–April–May"),
        "summary": _(
            "Seasonal guidance for the coastal Atlantic zone of West and Central Africa."
        ),
        "overview": _(
            "PRESAGG produces a consensus outlook for the first major rainy season "
            "along the Gulf of Guinea coast, a zone influenced by the ITCZ and the "
            "West African monsoon."
        ),
        "coverage": _(
            "Guinea, Liberia, Sierra Leone, Côte d’Ivoire, Ghana, Togo, Benin, "
            "Nigeria, Cameroon and Equatorial Guinea."
        ),
        "drivers": _(
            "ENSO, the equatorial and tropical Atlantic, the ITCZ and regional "
            "monsoon processes."
        ),
        "hazards": _(
            "Heavy rainfall, strong winds, damaging storms, dry spells and anomalous "
            "onset of the rains."
        ),
        "users": _(
            "Agriculture, water, infrastructure, disaster management and media users "
            "help identify likely impacts and useful actions."
        ),
        "priorities": _(
            "Build knowledge of Gulf of Guinea climate variability and improve the "
            "prediction of tropical Atlantic and monsoon interactions."
        ),
        "document_codes": ("PRESAGG",),
    },
    {
        "slug": "medcof",
        "code": "MEDCOF",
        "name": _("Mediterranean Climate Outlook Forum"),
        "region": _("Northern Africa and the Mediterranean"),
        "season": _("Winter and spring outlooks"),
        "summary": _(
            "Precipitation and temperature outlooks for the Mediterranean climate of "
            "Northern Africa."
        ),
        "overview": _(
            "MEDCOF assesses the winter and spring climate of the Mediterranean "
            "region, where mid-latitude circulation and tropical drivers both affect "
            "rainfall and temperature."
        ),
        "coverage": _(
            "The North African Mediterranean countries, including Morocco, Algeria, "
            "Tunisia, Libya and Egypt, within the wider Mediterranean forum."
        ),
        "drivers": _(
            "North Atlantic Oscillation, ENSO, Mediterranean and tropical Atlantic "
            "conditions, Eurasian snow, jet-stream variability and blocking patterns."
        ),
        "hazards": _(
            "Drought, flood, water shortage, summer heat, winter cold and abnormal "
            "seasonal onset."
        ),
        "users": _(
            "Water, agriculture, tourism, health, disaster management and planning "
            "communities use the outlook to anticipate seasonal risks."
        ),
        "priorities": _(
            "Improve North Atlantic and Mediterranean prediction, land-surface "
            "modelling and guidance for temperature, discharge and regional hazards."
        ),
        "document_codes": ("MEDCOF",),
    },
    {
        "slug": "swiocof",
        "code": "SWIOCOF",
        "name": _("South-West Indian Ocean Climate Outlook Forum"),
        "region": _("South-West Indian Ocean"),
        "season": _("November–April rainfall and tropical cyclone season"),
        "summary": _(
            "Consensus rainfall and tropical-cyclone guidance for island and coastal "
            "countries of the South-West Indian Ocean."
        ),
        "overview": _(
            "SWIOCOF addresses the distinctive maritime and island climates of the "
            "South-West Indian Ocean and supports common preparedness and response "
            "information for the coming season."
        ),
        "coverage": _(
            "Comoros, Madagascar, Mauritius, Mozambique, Réunion, Seychelles, South "
            "Africa and Tanzania."
        ),
        "drivers": _(
            "Indian Ocean sea-surface temperatures, the subtropical Indian Ocean "
            "Dipole, Southern Annular Mode, ENSO and atmosphere–ocean interactions."
        ),
        "hazards": _(
            "Tropical cyclones, torrential rainfall, flood, drought and damaging "
            "seasonal anomalies affecting islands and coastal areas."
        ),
        "users": _(
            "Disaster management, water, agriculture, health, tourism, trade and media "
            "communities participate in translating the outlook into action."
        ),
        "priorities": _(
            "Improve island-scale climate information, tropical-cyclone guidance and "
            "understanding of Indian Ocean climate drivers."
        ),
        "document_codes": ("SWIOCOF",),
    },
    {
        "slug": "sarcof",
        "code": "SARCOF",
        "name": _("Southern African Regional Climate Outlook Forum"),
        "region": _("Southern Africa"),
        "season": _("Main Southern African rainfall seasons"),
        "summary": _(
            "A consensus seasonal outlook coordinated for the Southern African region."
        ),
        "overview": _(
            "SARCOF brings regional and national climate experts together to develop "
            "a shared seasonal rainfall and temperature outlook for Southern Africa."
        ),
        "coverage": _("Southern African Development Community member countries."),
        "drivers": _(
            "ENSO, Indian and Atlantic Ocean conditions, regional circulation and "
            "land-surface influences on Southern African rainfall."
        ),
        "hazards": _(
            "Drought, flood, heat and rainfall timing anomalies affecting food, water, "
            "energy and disaster preparedness."
        ),
        "users": _(
            "NMHSs, regional organisations and sector users jointly interpret the "
            "outlook and develop advisories."
        ),
        "priorities": _(
            "Support national downscaling, impact-based forecasting, verification and "
            "consistent regional communication."
        ),
        "document_codes": ("SARCOF",),
    },
    {
        "slug": "ghacof",
        "code": "GHACOF",
        "name": _("Greater Horn of Africa Climate Outlook Forum"),
        "region": _("Greater Horn of Africa"),
        "season": _("March–May and October–December rainfall seasons"),
        "summary": _(
            "Regional consensus guidance for the principal rainfall seasons in the "
            "Greater Horn of Africa."
        ),
        "overview": _(
            "GHACOF combines climate monitoring, forecasts and expert interpretation "
            "to communicate likely seasonal conditions and impacts across the Greater "
            "Horn of Africa."
        ),
        "coverage": _("IGAD member countries and neighbouring areas of the Greater Horn."),
        "drivers": _(
            "Indian Ocean variability, ENSO, regional circulation and land–atmosphere "
            "conditions affecting the region's bimodal rainfall regimes."
        ),
        "hazards": _(
            "Drought, flood, extreme heat and abnormal onset, cessation or distribution "
            "of seasonal rainfall."
        ),
        "users": _(
            "Food security, agriculture, water, livestock, health, disaster-risk and "
            "humanitarian partners contribute to impact-based guidance."
        ),
        "priorities": _(
            "Connect regional forecasts with national and sector advisories and expand "
            "early action informed by forecast probabilities."
        ),
        "document_codes": ("GHACOF",),
    },
)
