# ACMAD Deployment Architecture

This guide describes ACMAD-specific responsibilities layered on the general ClimWeb architecture. Update it whenever a
service, hostname, storage boundary, external integration, or trust boundary changes.

## Logical architecture

```text
Public/editor/staff browser
          |
       DNS/TLS
          |
        nginx
          |
   Django + Wagtail web  <----> PostgreSQL/PostGIS
          |                         |
          +----> Redis <---- Celery worker / Celery beat
          |
          +----> public media/static storage
          +----> RCC data storage
          +----> private exports and staff-report storage
          +----> SMTP/Mailgun
          +----> Google Calendar/Meet and Shared Drive
          +----> ACMAD/SGBD/THREDDS and other product sources
```

## Compose services

The recorded integration configuration separates development and production profiles.

| Function | Development | Production |
| --- | --- | --- |
| PostgreSQL/PostGIS | `climweb_db_dev` | `climweb_db_prod` |
| Redis | `climweb_redis_dev` | `climweb_redis_prod` |
| Web application | `climweb_dev` | `climweb_prod` |
| Celery worker | `climweb_celery_worker_dev` | `climweb_celery_worker_prod` |
| Celery beat | `climweb_celery_beat_dev` | `climweb_celery_beat_prod` |
| nginx | `climweb_nginx` | `climweb_nginx_prod` |
| ACMAD initial product seed | Not separate | `climweb_acmad_seed_prod` |

Confirm service names from the exact release with:

```bash
docker compose --profile dev --profile prod config --services
```

Do not use `docker compose config` without a narrow selector in a shared transcript; fully resolved configuration can
contain sensitive values.

## Storage boundaries

| Storage | Classification | Recovery requirement |
| --- | --- | --- |
| PostgreSQL/PostGIS | Mixed public metadata and private operational/personal data | Encrypted database backup and tested restore |
| Public media | Public/publishable assets | Backup with database-consistent references |
| Static files | Generated release assets | Rebuildable, but validate release and collection |
| RCC data | Public operational datasets and derived files | Back up objects with matching database records |
| Private exports | Potentially sensitive form/submission exports | Restricted backup, retention, and deletion |
| Private staff reports | Confidential staff documents and draft material | Shared web/worker access, restricted backup, authorization tests |

Never move private reports or exports into public media to simplify deployment.

## Multi-site routing

Wagtail Sites allow the main ACMAD website, RCC, Summer School, and CLIMSA to share one application/database while using
separate hostnames and roots. Correct behavior depends on four aligned layers:

1. Public DNS.
2. TLS certificate SANs and renewal.
3. nginx server blocks/proxy configuration.
4. Wagtail Site hostname, port, and root page.

A successful HTTP response is insufficient; verify that the intended root, navigation, canonical links, assets, forms,
and cache keys belong to the requested hostname.

## Trust boundaries

- **Public:** published pages, public product files, approved media.
- **CMS/editorial:** authenticated Wagtail access governed by groups and page permissions.
- **Staff/HR:** private workspace with account-to-profile ownership and reviewer permission.
- **Operations:** importer dashboards, service configuration, worker/run history.
- **Infrastructure:** SSH, Compose, database, storage, DNS, TLS, and secrets.
- **External:** email, Google services, product sources, analytics, and monitoring.

Document data transferred across each boundary and the owner responsible for it.

## Change checklist

For architecture changes, record:

- diagram and service/storage impact;
- new configuration names and owner;
- secret provisioning/rotation path;
- migrations and backward compatibility;
- backup/recovery impact;
- monitoring and alert changes;
- permissions and data classification;
- deployment and rollback plan;
- updated operator/editor guides and acceptance results.
