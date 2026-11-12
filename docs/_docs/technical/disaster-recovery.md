# Disaster Recovery

This guide extends the basic Backup and Restore guide into an ACMAD recovery plan. Values for RPO, RTO, retention, and
off-site copies must be approved by ACMAD management and the infrastructure owner.

## Recovery scope

A complete recovery can require:

- PostgreSQL/PostGIS database;
- public media;
- RCC data objects;
- private exports;
- private staff reports and draft material;
- environment/secret re-provisioning;
- nginx, DNS, TLS, Wagtail Site, worker/beat, and external integration configuration;
- exact application release and migration state.

Static files should normally be rebuilt from the release, not treated as the only copy of source assets.

## Backup register

Record for each backup class: method, schedule, owner, storage, encryption, retention, off-site copy, checksum/integrity
check, last success, last restore test, RPO, and RTO. Monitoring must alert on missed or unusually small backups.

## Pre-release backup

Before a material release, verify command help on the exact release and create approved database/media backups:

```bash
python manage.py dbbackup --help
python manage.py mediabackup --help
python manage.py dbbackup
python manage.py mediabackup
```

Separately capture RCC data, private exports, and private staff reports according to their storage implementation. Record
identifiers, timestamps, sizes, checksums, and operator. Do not attach backup files to the handover report.

## Restoration rehearsal

Restoration is destructive to the target. Use an isolated environment and verified backup copies.

1. Record the incident/rehearsal objective and selected recovery point.
2. Provision a clean database with only the required PostGIS extension state described in the Backup and Restore guide.
3. Restore the database and media using the deployed command interfaces.
4. Restore RCC and private storage to their correct restricted locations.
5. Deploy the matching application release and configuration names.
6. Apply only migrations appropriate to the target release.
7. Reconcile Wagtail Site, DNS/nginx/TLS in the isolated test scope.
8. Start web, worker, and beat services.
9. Perform the validation matrix below.
10. Record duration, errors, data loss relative to RPO, and corrective actions.

## Validation matrix

- Main site and every programme-site root.
- CMS login and representative page revision/media.
- Product page, importer configuration, provenance, and run history.
- RCC page plus database-backed asset and stored file.
- Event/form record according to approved privacy access.
- Staff profile, assignment, protected report download, and authorization denial for another user.
- Celery task execution and scheduler registration.
- Email/Google integrations using controlled tests where authorized.
- Database counts/checksums and representative media/private files.

## Production recovery decision

An incident owner must approve recovery point, expected data loss, downtime, target environment, communication, and
whether to restore in place or rebuild alongside. Preserve the failed environment when forensic or data-reconciliation
work may be required.

Do not restore a database over production while web/worker processes can continue writing to it.

## After recovery

- Confirm deployed SHA and migration state.
- Rotate credentials if compromise is possible.
- Re-enable schedules in a controlled order and avoid duplicate imports/notifications.
- Reconcile data created after the recovery point.
- Monitor errors, queue depth, storage, and external integrations closely.
- Complete an incident report and update this guide from observed gaps.
