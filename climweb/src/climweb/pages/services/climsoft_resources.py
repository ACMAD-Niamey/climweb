"""Audited legacy Climsoft resources and their public catalogue metadata."""


CLIMSOFT_DOCUMENTS = (
    {
        "title": "Database Fundamentals",
        "filename": "database-fundamentals.pdf",
        "source_url": "https://rcc.acmad.org/manuelclimsoft/Database%20Fundamentals.pdf",
        "category": "Fundamentals",
        "description": "Climsoft Version 3.0 training manual covering relational database concepts and data management foundations.",
    },
    {
        "title": "Climsoft installation and reinstallation procedure",
        "filename": "climsoft-installation-and-reinstallation.pptx",
        "source_url": "https://rcc.acmad.org/manuelclimsoft/procedure_installation_et_reintallation_climsoft.pptx",
        "category": "Installation",
        "description": "French-language presentation covering installation and reinstallation procedures for Climsoft.",
    },
    {
        "title": "Climsoft Administrator Guide",
        "filename": "climsoft-administrator-guide.pdf",
        "source_url": "https://rcc.acmad.org/manuelclimsoft/Administrator%20Guide.pdf",
        "category": "Administration",
        "description": "System administration, database configuration, quality control, security, maintenance and backup guidance.",
    },
    {
        "title": "Climsoft Programmer Guide",
        "filename": "climsoft-programmer-guide.pdf",
        "source_url": "https://rcc.acmad.org/manuelclimsoft/Programmer%20Guide.pdf",
        "category": "Development",
        "description": "Technical guidance for extending and maintaining the Climsoft application.",
    },
    {
        "title": "Climsoft User Guide",
        "filename": "climsoft-user-guide.pdf",
        "source_url": "https://rcc.acmad.org/manuelclimsoft/User%20Guide.pdf",
        "category": "Operations",
        "description": "Operational guidance for working with climate data and standard Climsoft functions.",
    },
    {
        "title": "Climsoft Key Entry Guide",
        "filename": "climsoft-key-entry-guide.pdf",
        "source_url": "https://rcc.acmad.org/manuelclimsoft/Key%20Entry%20Guide.pdf",
        "category": "Data entry",
        "description": "Instructions for key-entry workflows and climate-observation data capture.",
    },
    {
        "title": "RClimDex User Manual",
        "filename": "rclimdex-user-manual.pdf",
        "source_url": "https://rcc.acmad.org/procedure/RClimDexUserManual.pdf",
        "category": "Climate indices",
        "description": "Guidance for calculating, quality-controlling and interpreting climate-extreme indices with RClimDex.",
    },
)

CLIMSOFT_DOCUMENTS_BY_TITLE = {item["title"]: item for item in CLIMSOFT_DOCUMENTS}
