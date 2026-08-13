"""Shared metadata for ACMAD's external product importers."""


PRODUCT_IMPORTS = (
    {
        "key": "multihazard",
        "label": "Continental Multi-Hazard Outlook",
        "product_names": ("Continental Multi-Hazard & Advisory Bulletin",),
        "source_label": "ACMAD SGBD/THREDDS",
        "enabled_setting": "ACMAD_MULTIHAZARD_AUTO_IMPORT",
        "interval_setting": "ACMAD_MULTIHAZARD_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-multihazard-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_multihazard_import",
        "command": "import_acmad_multihazard",
        "limit_setting": "ACMAD_MULTIHAZARD_IMPORT_LIMIT",
        "include_history": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "archive_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": (
                "https://sgbd.acmad.org/thredds/fileServer/FIT/BRIEFING/ARCHIVE/"
                "Hazard_Outlook/archive_hazard_outlook.html"
            ),
            "source_system": "ACMAD SGBD/THREDDS",
            "allowed_extensions": [".pdf"],
            "filename_pattern": (
                r"Continental_Hazard_Outlook_(?P<date>20\d{6})\.pdf$"
            ),
            "date_format": "%Y%m%d",
            "history_url_pattern": r"archive_hazard_outlook_20\d{2}\.html$",
            "request_headers": {},
        },
    },
    {
        "key": "rainfall",
        "label": "Daily Rainfall Monitoring",
        "product_names": ("Daily Rainfall Monitoring",),
        "source_label": "ACMAD SGBD/THREDDS GSMaP",
        "enabled_setting": "ACMAD_RAINFALL_AUTO_IMPORT",
        "interval_setting": "ACMAD_RAINFALL_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-daily-rainfall-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_daily_rainfall_import",
        "command": "import_acmad_daily_rainfall",
        "limit_setting": "ACMAD_RAINFALL_IMPORT_LIMIT",
        "include_history": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "archive_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": (
                "https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/"
                "verificationservice/OBS/ARCHIVE/GSMAP/archive_gsmap.html"
            ),
            "source_system": "ACMAD SGBD/THREDDS GSMaP",
            "allowed_extensions": [".png"],
            "filename_pattern": r"gsmap24_(?P<date>20\d{6})\.png$",
            "date_format": "%Y%m%d",
            "history_url_pattern": r"archive_gsmap_20\d{2}\.html$",
            "request_headers": {},
        },
    },
    {
        "key": "dekadal",
        "label": "Dekadal Climate Bulletin",
        "product_names": ("Dekadal Bulletin",),
        "source_label": "ACMAD RCC / SGBD THREDDS",
        "enabled_setting": "ACMAD_DEKADAL_AUTO_IMPORT",
        "interval_setting": "ACMAD_DEKADAL_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-dekadal-bulletin-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_dekadal_import",
        "command": "import_acmad_dekadal_bulletin",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": "https://rcc.acmad.org/dacadebulletin.php",
            "source_system": "ACMAD RCC / SGBD THREDDS",
            "allowed_extensions": [".pdf"],
            "filename_pattern": r"(?P<date>20\d{6}).*\.pdf$",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "monthly-climate",
        "label": "Monthly Climate Diagnostic Bulletin",
        "product_names": ("Monthly Climate Diagnostic Bulletin",),
        "source_label": "ACMAD RCC Monthly Climate Review THREDDS",
        "enabled_setting": "ACMAD_MONTHLY_CLIMATE_AUTO_IMPORT",
        "interval_setting": "ACMAD_MONTHLY_CLIMATE_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-monthly-climate-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_monthly_climate_import",
        "command": "import_acmad_monthly_climate",
        "limit_setting": "ACMAD_MONTHLY_CLIMATE_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
                "ClimateBulletin_TN/Monthly_Bulletin/catalog.xml"
            ),
            "source_system": "ACMAD RCC Monthly Climate Review THREDDS",
            "allowed_extensions": [".png"],
            "filename_pattern": (
                r"(?P<date>20\d{2}/[A-Za-z]{3})/.*/"
                r"Africa_rev_rfe_.*\.png$"
            ),
            "date_format": "%Y/%b",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "season-onset",
        "label": "Rainfall and Seasonal Onset Monitoring",
        "product_names": ("Rainfall and Seasonal Onset Monitoring",),
        "source_label": "ACMAD RCC Season Onset THREDDS",
        "enabled_setting": "ACMAD_SEASON_ONSET_AUTO_IMPORT",
        "interval_setting": "ACMAD_SEASON_ONSET_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-season-onset-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_season_onset_import",
        "command": "import_acmad_season_onset",
        "limit_setting": "ACMAD_SEASON_ONSET_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
                "climatemonitoringservice/Onset_Ops_Services/catalog.xml"
            ),
            "source_system": "ACMAD RCC Season Onset THREDDS",
            "allowed_extensions": [".jpeg", ".jpg"],
            "filename_pattern": (
                r"ecowas_Seasonal_Onset_(?:Obs|Fcst)_"
                r"(?P<date>20\d{6})\.jpe?g$"
            ),
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "climate-change",
        "label": "Climate Change and Climate Projections",
        "product_names": ("Climate Change and Climate Projections",),
        "source_label": "ACMAD RCC Highly Recommended Functions",
        "enabled_setting": "ACMAD_CLIMATE_CHANGE_AUTO_IMPORT",
        "interval_setting": "ACMAD_CLIMATE_CHANGE_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-climate-change-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_climate_change_import",
        "command": "import_acmad_climate_change",
        "limit_setting": "ACMAD_CLIMATE_CHANGE_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "source_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": "https://rcc.acmad.org/recomandation.php",
            "source_system": "ACMAD RCC Highly Recommended Functions",
            "allowed_extensions": [".pdf"],
            "filename_pattern": r"(?P<date>20\d{2})",
            "date_format": "%Y",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "annual-climate",
        "label": "Annual State of the Climate Report",
        "product_names": ("Annual State of the Climate Report",),
        "source_label": "ACMAD RCC Annual Climate Reports",
        "enabled_setting": "ACMAD_ANNUAL_CLIMATE_AUTO_IMPORT",
        "interval_setting": "ACMAD_ANNUAL_CLIMATE_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-annual-climate-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_annual_climate_import",
        "command": "import_acmad_annual_climate",
        "limit_setting": "ACMAD_ANNUAL_CLIMATE_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "source_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": "https://rcc.acmad.org/annualbulletin.php",
            "source_system": "ACMAD RCC Annual Climate Reports",
            "allowed_extensions": [".pdf"],
            "filename_pattern": r"(?P<date>20\d{2})",
            "date_format": "%Y",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "climate-watch",
        "label": "Climate Watch Bulletin",
        "product_names": ("Climate Watch Bulletin",),
        "source_label": "ACMAD RCC Drought Monitoring THREDDS",
        "enabled_setting": "ACMAD_CLIMATE_WATCH_AUTO_IMPORT",
        "interval_setting": "ACMAD_CLIMATE_WATCH_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-climate-watch-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_climate_watch_import",
        "command": "import_acmad_climate_watch",
        "limit_setting": "ACMAD_CLIMATE_WATCH_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
                "DroughtMonitoringService/catalog.xml"
            ),
            "source_system": "ACMAD RCC Drought Monitoring THREDDS",
            "allowed_extensions": [".pdf"],
            "filename_pattern": r"Bulletin_.*(?P<date>20\d{2})\.pdf$",
            "date_format": "%Y",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "rainfall-exceedance",
        "label": "Seasonal Rainfall Probability of Exceedance",
        "product_names": ("Seasonal Rainfall Probability of Exceedance",),
        "source_label": "ACMAD RCC Rainfall Exceedance THREDDS",
        "enabled_setting": "ACMAD_RAINFALL_EXCEEDANCE_AUTO_IMPORT",
        "interval_setting": "ACMAD_RAINFALL_EXCEEDANCE_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-rainfall-exceedance-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_rainfall_exceedance_import",
        "command": "import_acmad_rainfall_exceedance",
        "limit_setting": "ACMAD_RAINFALL_EXCEEDANCE_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
                "climatemonitoringservice/Probability_of_Exceedance/catalog.xml"
            ),
            "source_system": "ACMAD RCC Rainfall Exceedance THREDDS",
            "allowed_extensions": [".jpeg", ".jpg"],
            "filename_pattern": r"Excedence(?P<date>\d{3,4})mm\.jpe?g$",
            "date_format": "%Y",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "five-day-rainfall",
        "label": "5-Day Rainfall Probability Forecast",
        "product_names": ("5-Day Rainfall Probability Forecast",),
        "source_label": "ACMAD RCC 5-Day Rainfall Probability THREDDS",
        "enabled_setting": "ACMAD_FIVE_DAY_RAINFALL_AUTO_IMPORT",
        "interval_setting": "ACMAD_FIVE_DAY_RAINFALL_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-five-day-rainfall-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_five_day_rainfall_import",
        "command": "import_acmad_five_day_rainfall",
        "limit_setting": "ACMAD_FIVE_DAY_RAINFALL_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
                "climatemonitoringservice/Probability_of_Exceedance/5_Days/"
                "catalog.xml"
            ),
            "source_system": "ACMAD RCC 5-Day Rainfall Probability THREDDS",
            "allowed_extensions": [".jpeg", ".jpg"],
            "filename_pattern": (
                r"(?P<date>20\d{6})/.*/Probability_"
                r"(?:25|50|75|100|150)mm_5_Days[12]\.jpe?g$"
            ),
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "seasonal-verification",
        "label": "Seasonal Forecast Verification",
        "product_names": ("Seasonal Forecast Verification",),
        "source_label": "ACMAD RCC Seasonal Forecast Verification",
        "enabled_setting": "ACMAD_SEASONAL_VERIFICATION_AUTO_IMPORT",
        "interval_setting": "ACMAD_SEASONAL_VERIFICATION_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-seasonal-verification-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_seasonal_verification_import",
        "command": "import_acmad_seasonal_verification",
        "limit_setting": "ACMAD_SEASONAL_VERIFICATION_IMPORT_LIMIT",
        "include_history": True,
        "configurable_source": True,
        "source_option": "source_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": (
                "https://rcc.acmad.org/cartelongerange/cartelongrange.php"
            ),
            "source_system": "ACMAD RCC Seasonal Forecast Verification",
            "allowed_extensions": [".pdf", ".jpg"],
            "filename_pattern": (
                r"(?P<date>20\d{2})/.*/hs_(?:hg|md)(?:1[0-2]|[1-9])\.jpg$"
            ),
            "date_format": "%Y",
            "history_url_pattern": r"20\d{2}/cartelongrange\.php$",
            "request_headers": {},
        },
    },
    {
        "key": "model-performance",
        "label": "Seasonal Model Performance",
        "product_names": ("Seasonal Model Performance",),
        "source_label": "ACMAD RCC Seasonal Model Performance",
        "enabled_setting": "ACMAD_MODEL_PERFORMANCE_AUTO_IMPORT",
        "interval_setting": "ACMAD_MODEL_PERFORMANCE_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-model-performance-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_model_performance_import",
        "command": "import_acmad_model_performance",
        "limit_setting": "ACMAD_MODEL_PERFORMANCE_IMPORT_LIMIT",
        "include_history": True,
        "configurable_source": True,
        "source_option": "source_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": "https://rcc.acmad.org/longerange.php",
            "source_system": "ACMAD RCC Seasonal Model Performance",
            "allowed_extensions": [".jpg"],
            "filename_pattern": (
                r"(?P<date>20\d{2})/.*/hs_(?:hg|md)(?:[1-9]|[1-4]\d)\.jpg$"
            ),
            "date_format": "%Y",
            "history_url_pattern": r"20\d{2}/modelstatique20\d{2}\.php$",
            "request_headers": {},
        },
    },
    {
        "key": "cryosphere",
        "label": "Cryosphere and African Mountain Glaciers",
        "product_names": ("Cryosphere and African Mountain Glaciers",),
        "source_label": "ACMAD RCC Cryosphere",
        "enabled_setting": "ACMAD_CRYOSPHERE_AUTO_IMPORT",
        "interval_setting": "ACMAD_CRYOSPHERE_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-cryosphere-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_cryosphere_import",
        "command": "import_acmad_cryosphere",
        "limit_setting": "ACMAD_CRYOSPHERE_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": "source_url",
        "source_defaults": {
            "source_type": "html_archive",
            "source_url": "https://rcc.acmad.org/climatemonitoring.php",
            "source_system": "ACMAD RCC Cryosphere",
            "allowed_extensions": [".pdf"],
            "filename_pattern": r"(?P<date>2020).*\.pdf$",
            "date_format": "%Y",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "policy-briefs",
        "label": "Policy and Decision Briefs",
        "product_names": ("Continental Climate Policy", "Policy and Decision Briefs"),
        "source_label": "ACMAD SGBD/THREDDS Policy Briefs",
        "enabled_setting": "ACMAD_POLICY_BRIEFS_AUTO_IMPORT",
        "interval_setting": "ACMAD_POLICY_BRIEFS_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-policy-briefs-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_policy_briefs_import",
        "command": "import_acmad_policy_briefs",
        "limit_setting": "ACMAD_POLICY_BRIEFS_IMPORT_LIMIT",
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "https://sgbd.acmad.org/thredds/catalog/ACMAD/PROJECTS/CLIMSA/"
                "CDD/ACTIVITIES/SERVICES/Doc_Web/catalog.xml"
            ),
            "source_system": "ACMAD SGBD/THREDDS Policy Briefs",
            "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg"],
            "filename_pattern": r"(?P<date>20\d{6})",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "atmospheric-analysis",
        "label": "Atmospheric Analysis",
        "product_names": ("Atmospheric Analysis",),
        "source_label": "ACMAD Atmospheric Analysis THREDDS",
        "enabled_setting": "ACMAD_ATMOSPHERIC_ANALYSIS_AUTO_IMPORT",
        "interval_setting": "ACMAD_ATMOSPHERIC_ANALYSIS_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-atmospheric-analysis-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_atmospheric_analysis_import",
        "command": "import_acmad_atmospheric_analysis",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "history_catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://154.66.220.45:8080/thredds/catalog/ACMAD/CDD/"
                "ClimateBulletin_TN/NCEP_Clim_Next_Days/catalog.xml"
            ),
            "source_system": "ACMAD Atmospheric Analysis THREDDS",
            "allowed_extensions": [".png"],
            "filename_pattern": r"(?P<date>20\d{6})",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "heat-stress",
        "label": "Heat and Thermal Stress",
        "product_names": ("Heat and Thermal Stress",),
        "source_label": "ACMAD Heatwave THREDDS",
        "enabled_setting": "ACMAD_HEAT_STRESS_AUTO_IMPORT",
        "interval_setting": "ACMAD_HEAT_STRESS_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-heat-stress-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_heat_stress_import",
        "command": "import_acmad_heat_stress",
        "limit_setting": "ACMAD_HEAT_STRESS_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "http://154.66.220.45:8080/thredds/catalog/ACMAD/WWFD/"
                "forecastinservice/heatwave/catalog.xml"
            ),
            "source_system": "ACMAD Heatwave THREDDS",
            "allowed_extensions": [".png", ".jpg", ".jpeg"],
            "filename_pattern": r"(?P<date>20\d{6})",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "itd-itcz",
        "label": "ITD and ITCZ Monitoring",
        "product_names": ("ITD and ITCZ Monitoring",),
        "source_label": "ACMAD SGBD THREDDS / CSAG archive",
        "enabled_setting": "ACMAD_ITD_ITCZ_AUTO_IMPORT",
        "interval_setting": "ACMAD_ITD_ITCZ_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-itd-itcz-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_itd_itcz_import",
        "command": "import_acmad_itd_itcz",
        "limit_setting": "ACMAD_ITD_ITCZ_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "https://sgbd.acmad.org/thredds/catalog/FIT/ITD_MEAN_POSITION/"
                "catalog.xml"
            ),
            "source_system": "ACMAD SGBD THREDDS / CSAG archive",
            "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg"],
            "filename_pattern": r"(?P<date>20\d{6})",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "thunderstorm-nowcasting",
        "label": "Thunderstorm and Nowcasting",
        "product_names": ("Thunderstorm and Nowcasting",),
        "source_label": "ACMAD Satellite THREDDS",
        "enabled_setting": "ACMAD_NOWCASTING_AUTO_IMPORT",
        "interval_setting": "ACMAD_NOWCASTING_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-thunderstorm-nowcasting-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_nowcasting_import",
        "command": "import_acmad_thunderstorm_nowcasting",
        "limit_setting": "ACMAD_NOWCASTING_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "catalog_url",
        "source_defaults": {
            "source_type": "thredds_catalog",
            "source_url": (
                "https://sgbd.acmad.org/thredds/catalog/FIT/SATELLITE/catalog.xml"
            ),
            "source_system": "ACMAD Satellite THREDDS",
            "allowed_extensions": [".jpg", ".jpeg"],
            "filename_pattern": r"(?P<date>20\d{10})",
            "date_format": "%Y%m%d%H%M",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "climate-health",
        "label": "Climate and Health",
        "product_names": ("Climate and Health",),
        "source_label": "ACMAD WordPress Media",
        "enabled_setting": "ACMAD_CLIMATE_HEALTH_AUTO_IMPORT",
        "interval_setting": "ACMAD_CLIMATE_HEALTH_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-climate-health-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_climate_health_import",
        "command": "import_acmad_climate_health",
        "limit_setting": "ACMAD_CLIMATE_HEALTH_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "api_url",
        "source_defaults": {
            "source_type": "wordpress_api",
            "source_url": (
                "https://acmad.org/index.php/wp-json/wp/v2/media"
                "?search=meningitis&per_page=100"
            ),
            "source_system": "ACMAD WordPress Media",
            "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "filename_pattern": r"(?P<date>20\d{6})",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
    {
        "key": "seasonal-forecasts",
        "label": "Seasonal and Long-Range Forecasts",
        "product_names": (
            "Seasonal Forecast Maps",
            "Seasonal Outlook Bulletins",
            "Consensus Statements and Communiqués",
            "Recommendations and Summaries",
            "Technical Notes",
        ),
        "source_label": "ACMAD WordPress Media + THREDDS",
        "enabled_setting": "ACMAD_SEASONAL_FORECAST_AUTO_IMPORT",
        "interval_setting": "ACMAD_SEASONAL_FORECAST_IMPORT_INTERVAL_HOURS",
        "periodic_task_name": "import-acmad-seasonal-forecasts-automatically",
        "celery_task": "climweb.pages.products.tasks.run_acmad_seasonal_forecast_import",
        "command": "import_acmad_seasonal_forecasts",
        "limit_setting": "ACMAD_SEASONAL_FORECAST_IMPORT_LIMIT",
        "include_history": True,
        "history_only": True,
        "configurable_source": True,
        "source_option": "api_url",
        "source_option_multiple": True,
        "source_defaults": {
            "source_type": "wordpress_api",
            "source_url": (
                "https://acmad.org/index.php/wp-json/wp/v2/media"
                "?search=seasonal&per_page=100"
            ),
            "source_system": "ACMAD WordPress Media + THREDDS",
            "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "filename_pattern": r"(?P<date>20\d{6})",
            "date_format": "%Y%m%d",
            "history_url_pattern": "",
            "request_headers": {},
        },
    },
)


PRODUCT_IMPORTS_BY_KEY = {
    definition["key"]: definition for definition in PRODUCT_IMPORTS
}


def configured_importer_definition(importer):
    """Convert a database-backed importer into the shared registry shape."""
    source_defaults = dict(importer.default_source_config)
    return {
        "key": importer.key,
        "label": importer.label,
        "product_names": (importer.product_page.product.name,),
        "source_label": source_defaults.get("source_system", "Configured source"),
        "periodic_task_name": f"import-configured-product-{importer.key}",
        "celery_task": "climweb.pages.products.tasks.run_configured_product_import",
        "command": "import_configured_product",
        "include_history": True,
        "supports_retry": True,
        "configurable_source": True,
        "source_option": None,
        "source_defaults": source_defaults,
        "is_configured": True,
        "configured_importer_id": importer.pk,
        "product_page_id": importer.product_page_id,
        "product_item_type_id": importer.product_item_type_id,
        "default_enabled": importer.status == importer.STATUS_ACTIVE,
        "default_interval_hours": importer.default_interval_hours,
    }


def get_product_import_definitions():
    """Return built-in and dashboard-created importer definitions."""
    from .models import ConfiguredProductImporter

    configured = ConfiguredProductImporter.objects.select_related(
        "product_page__product", "product_item_type__category"
    )
    return (*PRODUCT_IMPORTS, *(configured_importer_definition(item) for item in configured))


def get_product_import_definition(family_key):
    definition = PRODUCT_IMPORTS_BY_KEY.get(family_key)
    if definition is not None:
        return definition

    from .models import ConfiguredProductImporter

    try:
        importer = ConfiguredProductImporter.objects.select_related(
            "product_page__product", "product_item_type__category"
        ).get(key=family_key)
    except ConfiguredProductImporter.DoesNotExist:
        return None
    return configured_importer_definition(importer)
