# Manage the Regional Climate Centre

This guide covers editorial and operational management of ACMAD's Regional Climate Centre (RCC) experience. Product
import configuration is documented separately in the Product Importer and ACMAD Product Migrations guides.

## Scope

The RCC implementation includes:

- a dedicated Regional Climate Center service landing page;
- Data Services, Climate Products, Climate Monitoring, Long-Range Forecasting, Training, Recommended Functions, and
  Coordination pages;
- ARC2 and CPC country/station datasets;
- climate indices, seasonal maps, reference climatologies, EIN15 archives, Climsoft resources, training resources,
  consensus forums, and forecast galleries;
- dashboard-managed import configuration and run history;
- a dedicated Wagtail Site and `nrcc.acmad.org` routing.

## Roles

| Role | Responsibility |
| --- | --- |
| RCC editor | Maintains page copy, images, links, resources, forums, and featured content |
| RCC operator | Tests sources, starts/stops imports, reviews runs, and validates published assets |
| Wagtail administrator | Manages navigation, permissions, Site records, and page structure |
| Infrastructure operator | Maintains storage, workers, schedules, DNS, nginx, TLS, backups, and monitoring |

Do not give infrastructure or superuser access merely to allow content editing.

## Page structure

The RCC landing page is a `ServicePage` whose service name is **Regional Climate Center**. RCC child pages use dedicated
page types. Avoid replacing them with generic pages because templates, navigation context, and resource links depend on
their types.

Recommended structure:

```text
Regional Climate Center
├── Data Services
├── Climate Products
├── Climate Monitoring
├── Long-Range Forecasting
├── Training
├── Recommended Functions
└── Coordination
```

Use the existing idempotent seed commands to create or reconcile standard content. Always inspect command help and test
against a non-production database before using a seed command on an established site.

```bash
python manage.py help | grep seed_rcc
python manage.py seed_rcc_data_services --help
python manage.py seed_rcc_climate_products --help
python manage.py seed_rcc_climate_monitoring --help
python manage.py seed_rcc_long_range_forecasting --help
python manage.py seed_rcc_training --help
python manage.py seed_rcc_recommended_functions --help
python manage.py seed_rcc_coordination --help
```

## Navigation

Open **Settings → Navigation settings** and maintain the RCC main menu. Link each item to the canonical RCC page or
approved resource. Preview the landing page, a child page, and a dataset view because all use the RCC navigation context.

After changing page slugs or moving pages:

1. Update navigation targets.
2. Review redirects.
3. Test dataset and gallery breadcrumbs.
4. Test the main ACMAD hostname and the RCC hostname.
5. Clear application/Wagtail caches using the approved deployment procedure if stale links remain.

## Dedicated hostname

After the live RCC landing page exists, an authorized operator can reconcile its Wagtail Site record:

```bash
python manage.py configure_rcc_subdomain --help
python manage.py configure_rcc_subdomain
```

The default is `nrcc.acmad.org` on port 443. The command does not configure DNS, nginx, or TLS. Complete those steps in
the Subdomain Deployment and TLS guides before public acceptance.

## Dataset and resource operations

RCC data files use the `rcc_data` storage backend. Database records and stored objects must be backed up together.

For any import:

1. Confirm the authoritative source, expected date/period, file format, and checksum or size where available.
2. Use the dashboard preview/test function or the command's dry-run/preview option when provided.
3. Record the operator, start/end time, source, command/configuration, and expected assets.
4. Review created, updated, skipped, and failed counts.
5. Open representative public files and verify content type, date, country/station, and download behavior.
6. Review worker logs for asynchronous imports.

Discover exact command options from the deployed release:

```bash
python manage.py help | grep -E 'import_rcc|sync_rcc'
python manage.py COMMAND_NAME --help
```

Never infer production options from an older branch.

## Scheduled jobs and failures

Dashboard configuration can override deployment defaults. Record the effective database configuration, not only `.env`
names. When a scheduled run is missing:

- verify Celery worker and beat health;
- verify the importer is enabled and its periodic task exists;
- run source test/preview;
- inspect the most recent run and logs;
- confirm the source hostname is permitted;
- check `rcc_data` capacity and permissions;
- retry only after deciding whether the failed run partially published assets.

Do not delete run history to hide a failure. Retain it as operational evidence.

## Editorial acceptance checklist

- [ ] All RCC page types and parent/child relationships are correct.
- [ ] RCC menu targets work on both ACMAD and RCC hostnames.
- [ ] Each catalogue/gallery contains expected current content.
- [ ] Country, station, period, and file metadata are accurate.
- [ ] Downloads return the intended file and content type.
- [ ] Empty and error states are understandable.
- [ ] Mobile navigation and dataset selectors are usable.
- [ ] Editors can update content without infrastructure permissions.

## Backup and recovery

Include the database, public media, and `rcc_data` storage in the recovery plan. A valid rehearsal must restore all three,
then test a page, a dataset record, its stored object, a gallery, and an importer configuration/history record.

## Related guides

- Product Importer Feature
- ACMAD Product Migrations
- Deployment
- Subdomain Deployment
- TLS Certificates
- Backup and Restore
