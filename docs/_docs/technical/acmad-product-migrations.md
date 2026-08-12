# ACMAD Product Migrations

## Purpose and scope

The ACMAD product migration moves file-based operational products from the legacy ACMAD website and data services into
Climweb. The implemented scope deliberately focuses on products delivered as PDF documents or image files. Legacy web
applications are not copied into the product catalogue; they can be linked from other pages where appropriate.

The migration is not a one-time copy. Each supported product family has an idempotent importer that can create its
Climweb product structure, discover current or historical source files, download them, publish dated product pages, and
record their provenance. The same importers support initial seeding, scheduled updates, and dashboard-triggered
historical imports.

## Completed product families

The following ten importer families have been implemented.

| Priority | Product family | Imported formats | Primary source | Default automatic interval | Historical import |
| --- | --- | --- | --- | --- | --- |
| 1 | Continental Multi-Hazard Outlook | PDF | ACMAD SGBD/THREDDS briefing archive | 6 hours | Yes |
| 2 | Daily Rainfall Monitoring | PNG | ACMAD SGBD/THREDDS GSMaP archive | 6 hours | Yes |
| 3 | Dekadal Climate Bulletin | PDF | ACMAD RCC and SGBD/THREDDS | 24 hours | Yes |
| 4 | Policy and Decision Briefs | PDF, PNG, JPG | ACMAD SGBD/THREDDS policy-brief catalogue | 24 hours | Yes |
| 5 | Atmospheric Analysis | PNG | ACMAD Atmospheric Analysis THREDDS | 6 hours | Yes |
| 6 | Heat and Thermal Stress | PNG, JPG | ACMAD Heatwave THREDDS | 6 hours | Yes |
| 7 | ITD and ITCZ Monitoring | PDF, PNG, JPG | ACMAD SGBD/THREDDS and CSAG archive | 6 hours | Yes |
| 8 | Thunderstorm and Nowcasting | JPG | ACMAD Satellite THREDDS | 1 hour | Yes |
| 9 | Climate and Health | PDF, PNG, JPG | Legacy ACMAD WordPress media API | 24 hours | Yes |
| 10 | Seasonal and Long-Range Forecasts | PDF, PNG, JPG | Legacy ACMAD WordPress media API and THREDDS | 24 hours | Yes |

Automatic importing is disabled by default. The intervals above are deployment defaults and can be changed separately
for each family in the Wagtail administration dashboard.

### Product structures created by the importers

- **Continental Multi-Hazard Outlook** publishes dated bulletin PDFs under the Continental Multi-Hazard & Advisory
  Bulletin product.
- **Daily Rainfall Monitoring** publishes dated GSMaP 24-hour rainfall observation maps.
- **Dekadal Climate Bulletin** publishes the available bulletin document set by issue date.
- **Policy and Decision Briefs** separates document briefs from image-based briefs.
- **Atmospheric Analysis** contains five 5-day atmospheric climatology maps and three daily synoptic analysis maps.
- **Heat and Thermal Stress** contains observed temperature products, heatwave indicators, and daily heat-index
  forecasts.
- **ITD and ITCZ Monitoring** accepts both bulletin documents and image products from the available archives.
- **Thunderstorm and Nowcasting** publishes timestamped satellite imagery rather than grouping all images under one
  calendar date.
- **Climate and Health** contains weekly meningitis bulletins, technical notes, vigilance/relative-humidity outlooks,
  and verification images discovered in the audited media collection.
- **Seasonal and Long-Range Forecasts** is a parent category whose five distinguishable product pages are listed below.

## Seasonal and Long-Range Forecast structure

Seasonal and Long-Range Forecasts is shown as a category on the public products page. Its imported assets are classified
into five reusable product types:

| Product type | Primary format | Content |
| --- | --- | --- |
| Seasonal Forecast Maps | JPG/PNG | Regional seasonal rainfall and climate outlook maps |
| Seasonal Outlook Bulletins | PDF | Seasonal and long-range outlook bulletins |
| Consensus Statements and Communiqués | PDF | Official regional climate outlook forum statements |
| Recommendations and Summaries | PDF | Decision guidance and summaries accompanying outlooks |
| Technical Notes | PDF | Supporting analysis and interpretation notes |

The importer searches audited WordPress terms and selected regional climate outlook forum THREDDS catalogues. It filters
out unrelated media such as banners, event photographs, agendas, training material, and presentations before classifying
the remaining files.

## How an import works

Each importer follows the same high-level process:

1. Read the built-in source definition or a source configuration saved through the dashboard.
2. Inspect an HTML archive, THREDDS XML catalogue, or WordPress media API response.
3. Match only approved file extensions and filename patterns.
4. Extract the issue date or issue timestamp from the source metadata or filename.
5. Apply the requested date range, processing limit, and ordering.
6. Create the required service, product, category, and item-type records when they do not already exist.
7. Download and validate the selected file.
8. Create or update the Wagtail image/document and publish the dated `ProductItemPage`.
9. Save the source URL, source system, issue date, checksum, status, attempt count, linked media, and destination page in
   `ProductSourceImport`.

The source URL is unique in the provenance table, which prevents normal scheduled runs from importing the same asset
twice. A refresh import can deliberately redownload an existing source. Supported importers can also retry previously
failed sources.

PDF files use generated document thumbnails. Product-category cards use the explicit introduction image when one is
configured, then fall back to the latest imported product image or PDF thumbnail, and finally to the configured default
thumbnail.

## Product Imports dashboard

Users with access to the Wagtail administration area can open **Product Imports** from the administration menu. The
overview page shows every importer family and summarizes:

- whether automatic importing is enabled;
- the active interval;
- imported and failed source counts;
- the latest imported source date and recent activity;
- importer health; and
- links to the created public product pages.

Each family has its own page for manual runs, scheduling, source configuration, and recent history.

### Manual historical imports

On an individual importer page:

1. Select **Preview only** first to inspect the proposed actions without downloading or publishing files.
2. Enter the inclusive **From date** and **To date**.
3. Set the maximum number of issue dates or records to process. The dashboard accepts 1–1000; this is a safety bound,
   not a statement about the size of the archive. Import a larger archive in date-range batches.
4. Optionally select **Refresh existing** or **Retry failures** where supported.
5. Run the preview, review its output, then repeat with **Import and publish**.

Manual work is queued in Celery so the request does not block the web process. The page polls live status and displays
the current phase, progress percentage, total/processed/imported/skipped/failed counters, and completion state. **View
output** opens the captured command output for a recent run.

An active manual import can be stopped. A queued run is cancelled before it starts; a running importer receives a
cooperative stop request and stops at its next safe progress checkpoint. Files successfully imported before the stop are
kept.

### Importer status and scheduling

Each family can be enabled or disabled independently from its importer page. Its automatic check interval can be set
from 1 to 720 hours. Saving either setting updates the persistent configuration and the corresponding
`django-celery-beat` periodic task.

Deployment environment variables provide the initial defaults. Dashboard values override those defaults. Therefore, a
family can remain enabled after a container restart without editing the Compose file again.

### Source and schema configuration

Every completed importer exposes a source configuration form with these fields:

- source type: HTML archive, THREDDS catalogue, or WordPress media API;
- source URL and source-system name;
- allowed extensions;
- filename regular expression containing a named `(?P<date>...)` group;
- Python date format matching the captured date;
- optional historical archive URL pattern; and
- optional HTTP request headers as JSON.

Use **Test connection** to validate access, and **Preview source** to inspect matching files before saving. **Restore
default configuration** removes the database override and returns the importer to its tested code-defined source and
schema.

Source customization changes discovery rules; it does not change an importer's product-specific classification logic.
For example, changing the Seasonal source does not remove its five product-type classifiers.

## Automatic imports and production seeding

Production requires the web application, Celery worker, Celery beat, database, Redis, and shared media volume. Celery
beat schedules checks, workers execute the imports, and Nginx serves media written to the shared volume.

The deployment-level settings are passed to the production web, worker, beat, and seed containers through
`docker-compose.yml`. Each family has an `*_AUTO_IMPORT`, `*_IMPORT_INTERVAL_HOURS`, and, where applicable,
`*_IMPORT_LIMIT` variable. Initial seeding is controlled by `ACMAD_INITIAL_IMPORT_ON_STARTUP`.

To seed all enabled families during a production deployment, set:

```dotenv
ACMAD_INITIAL_IMPORT_ON_STARTUP=True
```

Then run the one-shot seed service:

```bash
docker compose --profile prod run --rm climweb_acmad_seed_prod
```

The bootstrap command and all importers are idempotent. To force a seed independently of the environment flags:

```bash
docker compose --profile prod exec climweb_prod \
  manage bootstrap_acmad_products --force
```

To force only selected families, repeat `--product`:

```bash
docker compose --profile prod exec climweb_prod \
  manage bootstrap_acmad_products --force \
  --product rainfall \
  --product seasonal-forecasts
```

Valid family keys are `multihazard`, `rainfall`, `dekadal`, `policy-briefs`, `atmospheric-analysis`, `heat-stress`,
`itd-itcz`, `thunderstorm-nowcasting`, `climate-health`, and `seasonal-forecasts`.

## Command-line operation

Every family can also be run as a Django management command. For example, preview a historical rainfall range:

```bash
docker compose --profile prod exec climweb_prod \
  manage import_acmad_daily_rainfall \
  --include-history \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --limit 31 \
  --oldest-first \
  --dry-run
```

Remove `--dry-run` to import and publish the selected records. Use the dashboard for routine administration because it
retains the run history and exposes progress.

## Health states and troubleshooting

### Disabled

The deployment default or dashboard override has disabled the importer. Enable it from the individual importer page or
set the corresponding environment variable to `True`.

### Not seeded

The importer is enabled, but no successful `ProductSourceImport` record exists for the product names registered to that
family. This usually means the initial import has not run, the Celery worker is unavailable, or a restored database does
not contain matching provenance records. Run a preview, inspect its output, and then run the initial import.

### Attention

At least one failed provenance record exists. Open the family page and inspect its recent output/error. Confirm that the
source is reachable from inside the worker container and that its filename/schema still matches the configured rules.
Retry the failed range after resolving the source problem.

### Imports run but products are absent

Check all of the following:

- the Celery worker and Celery beat containers are running;
- all ACMAD environment variables are present in the worker and beat containers, not only the web container;
- the destination Product Index and required service categories exist and are published;
- the production database migrations have run;
- the web, worker, seed, and Nginx containers share the same production media volume; and
- the source host is reachable from the production server.

### Product thumbnails remain as placeholders

Confirm that at least one imported issue has an image or generated PDF thumbnail. The listing now falls back to the
latest imported issue when the category introduction image is empty. After deployment, clear the Wagtail/application
cache or wait for the configured cache lifetime before deciding that the new thumbnail fallback has failed.

## Implementation reference

The main implementation points are:

- `climweb/src/climweb/pages/products/import_registry.py` — importer registry, defaults, task names, and family keys;
- `climweb/src/climweb/pages/products/management/commands/import_acmad_*.py` — discovery and publishing logic;
- `climweb/src/climweb/pages/products/tasks.py` — scheduled and manual Celery tasks;
- `climweb/src/climweb/pages/products/import_monitoring.py` — dashboard health and statistics;
- `climweb/src/climweb/pages/products/import_progress.py` — progress accounting and cancellation checkpoints;
- `climweb/src/climweb/pages/products/import_sources.py` — source overrides, tests, and previews;
- `climweb/src/climweb/pages/products/import_scheduling.py` — persistent interval and enable/disable overrides; and
- `climweb/src/climweb/pages/products/models.py` — provenance, run, schedule, and source-configuration records.

Automated tests cover importer parsing and publishing, idempotency, automatic task enablement, bootstrap behavior, source
configuration, dashboard status, manual-run progress, cancellation, scheduling, and product thumbnail fallbacks.
