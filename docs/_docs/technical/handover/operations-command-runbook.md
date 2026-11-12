# Operations Command Runbook

These commands are templates for authorized operators. Read the surrounding warning and replace placeholders before
execution. Never paste secrets into a terminal that is being recorded or into a ticket, report, or Git commit.

## 1. Repository discovery

```bash
git remote -v
git branch --show-current
git status --short
git fetch --all --prune
git branch --all --no-color
git log --all --date=short --decorate --oneline --graph
```

Record exact reference heads without changing the checkout:

```bash
git rev-parse origin/develop
git rev-parse origin/production
git log -1 --date=iso-strict --pretty=fuller origin/develop
git log -1 --date=iso-strict --pretty=fuller origin/production
```

List work not reachable from a release branch:

```bash
git branch --no-merged origin/develop
git branch --no-merged origin/production
git log origin/develop..FEATURE_BRANCH --oneline --decorate
git diff --stat origin/develop...FEATURE_BRANCH
```

Do not delete a branch merely because it appears merged. First record its tip SHA, pull request, deployment state, and
whether it contains migrations, content, or operational documentation absent from the target.

## 2. Local development

Create `.env` from the sample and fill it locally without committing it:

```bash
cp .env.sample .env
make build
make up
docker compose --profile dev ps
make logs
```

Common lifecycle commands:

```bash
make migrate
make collectstatic
make createsuperuser
make shell
make restart
make down
```

Inspect services without printing resolved environment variables:

```bash
docker compose --profile dev config --services
docker compose --profile dev ps
docker compose --profile dev logs --tail=200 climweb_dev
docker compose --profile dev logs --tail=200 climweb_celery_worker_dev
docker compose --profile dev logs --tail=200 climweb_celery_beat_dev
```

## 3. Tests and release preflight

Run the isolated test-database workflow:

```bash
make test
```

Before promotion, review migrations and application configuration:

```bash
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py check --deploy
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py showmigrations
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py makemigrations --check --dry-run
```

Review the proposed release delta:

```bash
git log origin/production..RELEASE_BRANCH --oneline --decorate
git diff --stat origin/production...RELEASE_BRANCH
git diff --name-status origin/production...RELEASE_BRANCH
```

The release approver must explicitly review database migrations, environment-variable changes, nginx/TLS changes,
scheduled tasks, persistent-volume changes, and private-data paths.

## 4. Production pre-deployment evidence

Run on the production host with authorized access:

```bash
cd /PATH/TO/climweb
git status --short
git branch --show-current
git rev-parse HEAD
docker compose --profile prod ps
docker compose --profile prod config --services
```

Do not continue automatically when the production worktree is dirty. Identify and preserve intentional server-side
changes before deploying.

Capture recent service logs:

```bash
docker compose --profile prod logs --tail=200 climweb_prod
docker compose --profile prod logs --tail=200 climweb_celery_worker_prod
docker compose --profile prod logs --tail=200 climweb_celery_beat_prod
docker compose --profile prod logs --tail=200 climweb_nginx_prod
```

## 5. Backup before a material release

Confirm the installed command interface before executing a backup:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py dbbackup --help
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py mediabackup --help
```

Create database and media backups using the approved storage configuration:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py dbbackup
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py mediabackup
```

Record filenames, timestamps, sizes, storage destination, checksum, encryption state, retention classification, and the
person who verified them. A backup is not accepted until an isolated restore has been demonstrated.

## 6. Standard production deployment

The current repository guide defines this deployment sequence:

```bash
cd /PATH/TO/climweb
git pull --ff-only origin production
make build-prod
make down-prod
make up-prod
```

Then verify:

```bash
docker compose --profile prod ps
docker compose --profile prod logs --tail=200 climweb_prod
docker compose --profile prod logs --tail=200 climweb_celery_worker_prod
docker compose --profile prod logs --tail=200 climweb_celery_beat_prod
git rev-parse HEAD
```

The CI workflow currently performs a similar build/restart after a successful test job on a push to `production`.
Do not run a manual deployment concurrently with that workflow.

## 7. Application and migration verification

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py check --deploy
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py showmigrations
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py get_climweb_version
```

If static files were not collected by the entrypoint, use the documented release procedure before running:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py collectstatic --noinput
```

## 8. Programme subdomains

Inspect command help first:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py configure_rcc_subdomain --help
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py configure_climsa_subdomain --help
```

The documented idempotent reconciliation commands are:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py configure_rcc_subdomain
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py configure_climsa_subdomain --create
```

Run them only after DNS, TLS SAN coverage, nginx configuration, canonical Wagtail pages, and the intended hostname/port
have been reviewed. See the subdomain and TLS guides.

## 9. Product and RCC import operations

List relevant commands from the running release:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py help | grep -E 'import_acmad|import_rcc|sync_rcc|bootstrap_acmad|seed_rcc'
```

Read exact options before running an importer:

```bash
docker compose --profile prod exec -T climweb_prod \
  python /climweb/web/src/climweb/manage.py COMMAND_NAME --help
```

Prefer the product importer dashboard's **Test connection** and **Preview source** controls before saving or running a
configured source. For command-line execution, record the command, source configuration, start/end time, result,
created/updated/skipped counts, error log, operator, and resulting public URLs.

Check workers when a queued or scheduled import does not run:

```bash
docker compose --profile prod ps climweb_celery_worker_prod climweb_celery_beat_prod
docker compose --profile prod logs --tail=300 climweb_celery_worker_prod
docker compose --profile prod logs --tail=300 climweb_celery_beat_prod
```

## 10. HTTP, TLS, and routing checks

Run from an approved machine with external network access:

```bash
curl -fsSIL https://acmad.org/
curl -fsSIL https://nrcc.acmad.org/
curl -fsSIL https://summerschool.acmad.org/
curl -fsSIL https://climsa.acmad.org/
```

Review certificate identity and expiry without exposing private material:

```bash
openssl s_client -connect acmad.org:443 -servername acmad.org </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

Repeat for every production hostname. Verify the page belongs to the intended Wagtail Site rather than accepting a
successful status code alone.

## 11. Restoration rehearsal

Restoration is destructive to the target database. Perform it only in an isolated, explicitly approved rehearsal
environment. Never test restoration against the live production database.

Inspect the command interface:

```bash
python manage.py dbrestore --help
python manage.py mediarestore --help
```

Record the isolated environment, backup identifiers, database preparation, exact commands, duration, errors, restored
record counts, media spot checks, application smoke tests, and recovery owner. Follow the backup/restore guide for the
required PostGIS-only database state.

## 12. Incident and rollback discipline

1. Stop the release and preserve logs, failing SHA, timestamps, affected domains, and symptoms.
2. Decide whether the safest response is configuration correction, forward fix, or a reviewed Git revert.
3. Do not use `git reset --hard`, delete persistent volumes, or restore a database without explicit incident authority.
4. If reverting code, create and review a revert commit, run tests, deploy through the normal release path, and confirm
   migration compatibility.
5. Restore data only when the incident owner has selected a verified backup and accepted the recovery point.
6. Record the incident, resolution, data impact, follow-up owner, and preventive action.

## 13. Evidence to retain after every release

- approved release SHA and pull request;
- CI/test result;
- migration list and outcome;
- pre-release backup identifiers;
- deployed SHA;
- service health output;
- public and protected smoke-test results;
- importer/worker verification;
- rollback decision and result, if applicable;
- operator, reviewer, timestamps, exceptions, and follow-up actions.
