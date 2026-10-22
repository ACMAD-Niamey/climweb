# Product Importer Feature

## Overview

The Product Importer feature discovers dated PDF and image products from external archives and publishes them into an
existing Climweb Product Page. It supports both built-in ACMAD importers and controlled importers created by an
administrator from the Wagtail dashboard.

The feature provides one operational workflow for:

- monitoring all product importers;
- previewing and importing historical date ranges;
- following import progress without refreshing the page;
- stopping queued or running imports;
- inspecting full command output and error messages;
- retrying failed imports;
- enabling automatic imports and setting an interval per product;
- testing and changing source/schema configuration; and
- creating, editing, archiving, restoring, and auditing dashboard-created importers.

Only file-based products are supported. A dashboard-created importer accepts PDF, JPG, JPEG, PNG, GIF, and WebP files.
Interactive web applications should be linked from an appropriate page instead of being copied by this feature.

## Concepts and data flow

An importer connects four parts of Climweb:

```text
External archive
    ↓ discover files and issue dates
Importer definition and source schema
    ↓ download, validate, and deduplicate
Wagtail document/image and Product Item Page
    ↓ record the result
Provenance, run history, progress, and audit records
```

| Record | Purpose |
| --- | --- |
| `ProductSourceImport` | Provenance for one external source file, including URL, checksum, issue date, status, attempts, media, and destination page |
| `ProductImportRun` | One dashboard-requested preview/import, with parameters, progress, output, error, requester, and timestamps |
| `ProductImportSchedule` | Persistent enable/disable override and interval for one importer |
| `ProductImportSourceConfig` | Dashboard source/schema override for one importer |
| `ConfiguredProductImporter` | Definition of an importer created in the dashboard |
| `ConfiguredProductImporterAuditEvent` | Immutable history of lifecycle and configuration changes to a dashboard-created importer |

The source URL is the normal deduplication key. A scheduled import therefore skips a file already recorded as imported.
**Refresh existing** deliberately downloads it again, while **Retry failures** allows supported importers to process
provenance records that previously failed.

## Importer types

### Built-in importers

Built-in importers are defined in code. They contain product-specific discovery, classification, and publishing logic.
They are appropriate when one issue contains several files, requires special grouping, or needs custom rules. Examples
include Continental Multi-Hazard Outlook, Daily Rainfall Monitoring, Heat and Thermal Stress, and Seasonal and
Long-Range Forecasts.

An administrator can change a built-in importer's source/schema override, enabled state, schedule, and manual-run
parameters. Changing the source does not replace its code-defined classification rules.

See [ACMAD Product Migrations](acmad-product-migrations.md) for the complete built-in inventory and source details.

### Dashboard-created importers

A dashboard-created importer is a reusable, database-backed importer for a straightforward dated PDF or image feed.
Each discovered file is attached to one selected Product Item Type on one existing Product Page.

This option is suitable when:

- each source file represents one dated issue;
- the issue date can be extracted using a filename regular expression;
- all matching files belong to the same destination Product Item Type; and
- no executable code, credentials, or product-specific classification is required.

Use a built-in importer when a source needs multi-file issue grouping, specialized classification, unusual API logic,
or a product structure that the generic importer cannot represent safely.

## Accessing the dashboard

Sign in to Wagtail and select **Product Imports**. The feature is available to superusers and users with permission to
access the Wagtail administration area.

The overview displays each importer, its health, schedule, imported and failed source counts, latest source date, recent
activity, and links to its public Product Pages. Select **Manage imports** to open an individual importer.

### Health states

| State | Meaning | Recommended action |
| --- | --- | --- |
| Healthy | Successful provenance exists and no unresolved failure is affecting the status | No action required |
| Attention | One or more source records failed | Inspect the error/output, correct the cause, then retry |
| Not seeded | The importer is enabled but has no successful matching provenance | Run a preview and initial import; verify the worker if it remains queued |
| Disabled | Automatic importing is disabled | Enable it only after validating the source |
| Archived | A dashboard-created importer was retired | Restore it as a draft before editing or running it |

## Running a manual import

Open an individual importer and use **Manual historical import**:

1. Select **Preview only (dry run)**.
2. Enter an inclusive **From date** and **To date**.
3. Set **Limit** between 1 and 1000. The limit is a safety bound on issue dates or records, so process larger archives
   in date-range batches.
4. Select **Refresh existing** only when already imported source files must be downloaded again.
5. Select **Retry failures** when failed provenance records should be reconsidered and the importer supports it.
6. Select **Queue import** and review the result.
7. When the preview is correct, repeat the request using **Import and publish**.

Manual imports execute through Celery rather than inside the web request. The history row reports the current phase,
percentage, processed total, imported count, failed count, skipped count, status, and requester. The page polls for
updates while a run is active.

### Viewing output and errors

Use **View output** to open the captured management-command output in a modal. Long error messages are shortened to 120
characters in the history table; select **View error** to read the complete message in the modal.

Output and errors are retained on the run record. Closing the modal or leaving the page does not stop the import.

### Stopping an import

Select **Stop import** on a queued or running row and confirm the request.

- A queued run is cancelled before it starts.
- A running importer receives a cooperative stop request and exits at its next safe progress checkpoint.
- Files successfully imported before that checkpoint remain published and recorded.

The status changes through **Stopping** to **Stopped** where necessary. Force-terminating the worker is not part of the
dashboard workflow because it can interrupt a file or database operation at an unsafe point.

### Retrying a failed import

A failed history row contains **Retry import**. After confirmation, Climweb creates a new queued run that reuses the
original:

- product family and mode;
- from/to dates;
- record limit; and
- refresh-existing setting.

The new run enables failed-record retry and is labelled **Retry failures** in history. The original failed run, output,
error, task identifier, and timestamps remain unchanged for diagnosis and audit purposes.

Only a run whose current status is **Failed** can be retried. The server validates this even if a request is submitted
without using the dashboard button. If queueing itself fails, the new run is marked failed with the queue error.

## Automatic imports

On an individual importer page, use **Enable importer** or **Disable importer** to control automatic execution. Set
**Run every (hours)** to a value from 1 to 720 and save the schedule.

The saved dashboard state updates the corresponding `django-celery-beat` periodic task and overrides the deployment
default. The interval remains stored when an importer is disabled, ready to be reused if it is enabled again.

Automatic execution requires all of the following:

- a running Celery worker;
- a running Celery Beat scheduler;
- Redis and the database;
- network access from the worker to the source;
- applied database migrations; and
- a media volume shared by the web, worker, and web-server containers.

## Source and schema configuration

Each supported importer provides these fields:

| Field | Description | Example |
| --- | --- | --- |
| Source type | HTML archive/directory, THREDDS XML catalogue, or WordPress media API | `html_archive` |
| Source URL | Public endpoint inspected for files | `https://data.example.org/archive/index.html` |
| Source name | Human-readable provenance label | `Example Climate Archive` |
| Allowed extensions | Comma-separated file suffixes | `.pdf, .jpg` |
| Filename pattern | Regular expression with a named `date` capture | `bulletin_(?P<date>20\d{6})\.pdf$` |
| Date format | Python format matching the captured value | `%Y%m%d` |
| Historical archive pattern | Optional expression for linked archive pages | `archive_20\d{2}\.html$` |
| Request headers | Optional JSON object containing non-secret string headers | `{"Accept": "text/html"}` |

The filename pattern must contain `(?P<date>...)`. For example, the filename
`bulletin_20260813.pdf` matches:

```text
bulletin_(?P<date>20\d{6})\.pdf$
```

with date format:

```text
%Y%m%d
```

Use **Test connection** to check access and report the number of matching files. Use **Preview discovered files** to
inspect issue dates and URLs before saving. For a built-in importer, **Restore default configuration** deletes the
database override and returns to the source/schema tested in code.

Do not enter passwords, cookies, API tokens, authorization headers, or other secrets. Dashboard-created importers reject
common credential-bearing headers, and the feature does not execute user-provided code.

## Creating an importer from the dashboard

Before beginning, create and publish the destination Product Page and ensure its Product snippet contains the required
Product Category and Product Item Type. Then select **Create importer** from the Product Imports overview.

Complete the following:

1. **Importer name** — the operator-facing label.
2. **Importer key** — a unique stable slug, such as `regional-drought-bulletin`.
3. **Destination Product Page** — where dated Product Item Pages will be published.
4. **Destination Product Type** — the document/image block type used on each issue.
5. **Status** — use **Draft** until the source has been verified; **Active** enables its schedule.
6. **Default interval** — from 1 to 720 hours.
7. Source/schema fields described above.

Select **Preview discovered files** and confirm that the expected files and issue dates appear. Creation is rejected when
the source preview finds no matching dated files. Select **Create importer** only after the preview is correct.

The selected Product Item Type must belong to the Product attached to the selected Product Page. The importer key cannot
duplicate a built-in key and becomes permanent after creation because schedules, runs, provenance, and audit records use
it as their stable identifier.

The generic importer enforces a 50 MiB limit for each downloaded file. It calculates a SHA-256 checksum, creates or
updates Wagtail media, publishes a dated Product Item Page, and records provenance. Normal repeated checks are
idempotent.

## Editing and lifecycle management

### Editing

Select **Edit importer** to change its name, destination, Product Item Type, status, interval, or source/schema. The key
is read-only. Saving requires a successful discovery result containing at least one matching file.

Changes to a dashboard-created importer, its source, status, and schedule are shown under **Importer audit trail**, with
the date, action, user, and changed values.

### Archiving

Use **Archive importer** when a dashboard-created importer should no longer run. Archiving:

- is blocked while a run is queued, running, or stopping;
- disables its saved schedule and Celery Beat task;
- blocks manual and direct generic-command execution;
- hides source, schedule, and manual-run forms; and
- preserves provenance, run history, output, errors, and audit events.

Archiving is preferable to deleting an importer because historical records retain their meaning.

### Restoring

Select **Restore as draft** to return an archived importer to an editable state. Restoration does not automatically enable
automatic imports. Review the source, run a preview, and then enable the importer when it is ready.

## Command-line operation

Routine manual imports should use the dashboard because it records requester, progress, output, and status. A
dashboard-created importer can also be invoked directly for diagnosis:

```bash
docker compose --profile prod exec climweb_prod \
  manage import_configured_product regional-drought-bulletin \
  --include-history \
  --from-date 2026-01-01 \
  --to-date 2026-12-31 \
  --limit 100 \
  --oldest-first \
  --dry-run
```

Remove `--dry-run` to publish. Useful optional flags include `--refresh`, `--retry-failures`, and
`--continue-on-error`. An archived importer cannot be run by this command.

Built-in importers have their own `import_acmad_*` management commands. Refer to
[ACMAD Product Migrations](acmad-product-migrations.md#command-line-operation) for an example.

## Troubleshooting

### A run remains queued

Confirm that the Celery worker is running, connected to Redis, and consuming the configured queue. A running web
container alone cannot execute the job.

### Automatic runs do not start

Confirm Celery Beat is running and inspect the importer's saved enabled state and interval. Restart web, worker, and beat
services after deploying task-registration changes.

### The source test succeeds but discovers zero files

Compare actual filenames with the allowed extensions, filename pattern, and date format. Ensure the regular expression
contains `(?P<date>...)`. For historical files, also verify the historical archive pattern.

### The importer reports Not seeded after being enabled

Run a preview and then an initial import. If a run fails or remains queued, inspect its full error/output. Also confirm
that restored provenance records refer to the product names registered for that importer.

### Imported records exist but files are missing publicly

Confirm that the worker and web server share the same media volume, that Nginx serves that volume, and that the Product
Page and Product Item Page are live. Apply pending migrations and clear application/Wagtail caches after deployment.

### A retry fails again

Open **View error** and **View output** on both the original and retry runs. Correct source reachability, filename/schema,
file-size, destination, or media-volume problems before retrying again. Repeated retries do not repair a persistent
configuration problem.

## Deployment checklist

After deploying importer changes:

1. Run `manage migrate`.
2. Restart the web application, Celery worker, and Celery Beat.
3. Confirm Redis, database, and shared media storage connectivity.
4. Open **Product Imports** and verify importer health and schedules.
5. Preview one small date range.
6. Queue an import and confirm live progress, output/error modals, stop controls, and history.
7. If a known failure is available, verify **Retry import** creates a separate queued run.

## Implementation reference

| File | Responsibility |
| --- | --- |
| `import_registry.py` | Built-in definitions and conversion of database-backed definitions |
| `import_sources.py` | Source resolution, testing, preview, and overrides |
| `import_monitoring.py` | Health, counts, activity, and dashboard summaries |
| `import_progress.py` | Progress accounting and cooperative cancellation |
| `import_scheduling.py` | Persistent schedule synchronization with Celery Beat |
| `tasks.py` | Manual and automatic Celery tasks |
| `views.py` | Dashboard actions, validation, queueing, retry, and lifecycle workflows |
| `management/commands/import_configured_product.py` | Generic dashboard-created importer execution |
| `management/commands/import_acmad_*.py` | Product-specific built-in importers |
| `models.py` | Provenance, runs, schedules, source overrides, configured importers, and audit events |

The Products test suite covers registry behavior, source/schema validation, manual queueing, progress, stopping, retry,
scheduling, importer creation/editing, archive/restore behavior, audit history, generic publishing, and built-in product
importers.
