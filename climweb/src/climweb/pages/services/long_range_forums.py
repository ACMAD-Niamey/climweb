"""Regional Climate Outlook Forum content used by the RCC public pages."""

from django.utils.translation import gettext_lazy as _


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
