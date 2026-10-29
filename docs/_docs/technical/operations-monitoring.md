# Operations, Monitoring, and Incident Response

This runbook defines what ACMAD operators should observe and how to respond. Replace example thresholds with approved
service objectives and connect them to the institutional alerting platform.

## Daily checks

- Public availability and correct site routing for every production hostname.
- TLS validity and upcoming expiry.
- Web, database, Redis, worker, beat, nginx, and seed-job state.
- Recent application/nginx errors and authentication anomalies.
- Failed or overdue product/RCC imports.
- Celery queue backlog and scheduled-task execution.
- Email notification failures or unusual bounce/suppression activity.
- Google Drive synchronization failures when enabled.
- Disk/volume capacity for database, media, RCC data, backups, private exports, and staff reports.
- Most recent database/media/private-data backup status.

## Safe status commands

```bash
docker compose --profile prod ps
docker compose --profile prod logs --tail=200 climweb_prod
docker compose --profile prod logs --tail=200 climweb_celery_worker_prod
docker compose --profile prod logs --tail=200 climweb_celery_beat_prod
docker compose --profile prod logs --tail=200 climweb_nginx_prod
```

Use centralized logging/observability when configured. Do not paste logs containing tokens, email addresses, form data,
staff filenames, or request bodies into public issues.

## External checks

For every hostname, monitor:

- DNS resolution;
- TCP/TLS negotiation;
- certificate hostname and expiry;
- HTTP status and redirect chain;
- expected page marker/site identity;
- representative static and media asset;
- response time and error rate.

Staff/CMS health checks must use dedicated controlled accounts and avoid storing session cookies in monitoring output.

## Importer monitoring

Track each enabled importer by owner, source, schedule, last attempt, last success, expected freshness, last published
issue, and current error. Alert on missed freshness rather than job failure alone: a job can succeed while publishing no
new or wrong-period content.

When an import fails:

1. Preserve run ID, timestamps, source/config revision, logs, and partial results.
2. Test source connectivity and preview matching assets.
3. Verify worker/beat, credentials/allowlists, storage capacity, and parser expectations.
4. Decide whether the run partially published content.
5. Correct the cause, then retry through the supported dashboard/command.
6. Validate public output and close the incident with evidence.

## Severity model

| Severity | Example | Initial response |
| --- | --- | --- |
| Critical | Site-wide outage, data loss, credential compromise, public private-file exposure | Escalate immediately; preserve evidence; restrict access/change window |
| High | Major hostname/workflow unavailable, imports broadly stale, staff authorization failure | Assign incident owner and begin controlled mitigation |
| Medium | One importer/page/integration degraded with workaround | Record, contain, and schedule repair |
| Low | Cosmetic/editorial defect without data/security impact | Add to maintenance backlog |

## Incident procedure

1. Name an incident owner and recorder.
2. Record start time, detection, affected users/hostnames, known data exposure/loss, and current SHA.
3. Preserve relevant logs and configuration names without disclosing secrets.
4. Contain harm before optimizing availability.
5. Choose configuration correction, forward fix, reviewed revert, or verified data restore.
6. Test the recovery path and obtain authority for destructive/data-changing actions.
7. Verify affected and adjacent services after recovery.
8. Communicate closure and remaining risk.
9. Complete a post-incident review with owners and dates.

Never use `git reset --hard`, delete persistent volumes, or restore production data as an improvised rollback.

## Monitoring ownership record

For every dashboard/alert, record signal, threshold, notification channel, primary/backup owner, quiet hours, escalation,
runbook link, last test, and retention. An alert without an accountable responder is not operational coverage.
