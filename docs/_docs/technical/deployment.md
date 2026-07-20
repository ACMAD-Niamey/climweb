# Deployment

This describes how ACMAD's own instance is actually built and deployed - the concrete CI/CD pipeline and server
setup, as opposed to a generic Docker installation guide. For general Docker deployment instructions applicable to
any ClimWeb instance, see [wmo-raf/climweb-docker](https://github.com/wmo-raf/climweb-docker).

## Branches

- **`develop`** - active development branch. Pushes and PRs run the test job only.
- **`production`** - deploys automatically on every push. Pushes and PRs also run the test job first; the deploy
  job only runs if tests pass.

## CI/CD pipeline

Defined in [`.github/workflows/climweb-ci-cd.yml`](../../../.github/workflows/climweb-ci-cd.yml). Two jobs:

### `test`

Runs on every push/PR to `develop` or `production`. Rather than installing Python/PostGIS/GDAL directly on the
GitHub Actions runner (which would drift from what the Dockerfile actually specifies), it builds and runs the same
dev Docker image used locally:

1. Writes a throwaway `.env` with CI-only values (not real secrets).
2. `docker compose --profile dev up -d --build`.
3. Waits for `climweb_dev`'s startup sequence (db/redis wait, migrate, collectstatic - see
   `climweb/docker/docker-entrypoint.sh`) to finish, by polling its logs for `Running Development Server`.
4. Runs the test suite: `python /climweb/web/src/climweb/manage.py test --settings=climweb.config.settings.test`.
5. Tears the stack down (`docker compose --profile dev down -v`), even on failure.

### `deploy`

Only runs on push to `production`, and only after `test` passes. SSHes into the production host (a Vultr VM) using
a deploy key stored in the `VULTR_SSH_KEY` repo secret (along with `VULTR_USER`/`VULTR_IP`), then:

```bash
cd climweb
git pull origin production

make build-prod
make down-prod
make up-prod

docker builder prune -af
```

`make build-prod`/`up-prod`/`down-prod` (see `Makefile`) all operate on the `prod` Compose profile
(`docker compose --profile prod ...`) - distinct from the `dev` profile used for local development and CI tests.
`docker builder prune -af` clears the build cache afterward so it doesn't grow unbounded on the VM over time.

## Manual deployment

To redeploy without waiting for a push to `production` (e.g. to pick up a change already merged, or to retry after
a transient failure like a flaky `apt-get` mirror mid-build), run the same three commands directly on the
production host:

```bash
cd climweb
git pull origin production
make build-prod
make down-prod
make up-prod
```

## Server-side configuration not covered by the pipeline

The pipeline only rebuilds and restarts the application containers - it does not touch nginx configuration, TLS
certificates, or Wagtail Site records. Those are managed directly on the production host and are not automated:

- **nginx config** - which file is active is controlled by the `NGINX_CONFIG_PROD` env var in `.env` (see
  `docker-compose.yml`, `climweb_nginx_prod` service). Changing it requires
  `docker compose up -d --force-recreate climweb_nginx_prod` to take effect.
- **TLS certificates** - issued and renewed via `certbot` running on the host (not containerized). See
  [subdomain-deployment.md](subdomain-deployment.md) for the webroot/renewal-hook setup this depends on.
- **Wagtail Sites, page content, CMS settings** - managed through the Wagtail admin, as with any ClimWeb instance.

[subdomain-deployment.md](subdomain-deployment.md) documents the additional, ACMAD-specific pieces of this: serving
a section of the site on its own subdomain.
