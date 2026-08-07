# Hosting a Section on Its Own Subdomain

This is a customization made in the [ACMAD fork](https://github.com/ACMAD-Niamey/climweb) of Climweb, not part of
the upstream project. It is not required for a standard Climweb deployment.

Upstream references:

- Climweb project: https://github.com/wmo-raf/nmhs-cms
- Reference Docker deployment: https://github.com/wmo-raf/climweb-docker

## Background

A standard Climweb deployment serves a single Wagtail Site on a single hostname. ACMAD's deployment additionally
serves the Summer School section (`SummerSchoolIndexPage` and its children) on its own subdomain,
`summerschool.acmad.org`, sharing the same application, database, and page tree as the main site at
`new.acmad.org`. This is done using Wagtail's built-in multi-site support rather than a separate deployment.

This page documents how that was wired up, and the gotchas that came with it, so the same pattern can be repeated
for a future subdomain without re-discovering each issue from scratch.

## 1. nginx: two-phase config

TLS can't be issued for a new hostname until nginx is already serving `/.well-known/acme-challenge/` for it over
plain HTTP - but nginx also can't start a `443 ssl` server block that points at a certificate file which doesn't
exist yet. So the rollout goes through two nginx configs:

- `deploy/nginx/nginx.prod.ssl.presummerschool.conf` - bootstrap config. The existing site (`new.acmad.org`) is
  untouched on 443; the new subdomain is added on plain port 80 only, proxying straight to the app, just long
  enough for `certbot certonly --webroot` to complete its HTTP-01 challenge.
- `deploy/nginx/nginx.prod.ssl.conf` - the permanent config, swapped in once the certificate exists. Both domains
  get the same 80 (redirect) + 443 (ssl) pair.

Switch between them via the `NGINX_CONFIG_PROD` env var, then `docker compose up -d --force-recreate
climweb_nginx_prod`.

**Gotcha - duplicate `listen` options:** `ipv6only=on` is a socket-level option and can only be declared once per
unique `address:port` across the whole nginx process, not once per server block. If more than one `server {}`
block for the same port (e.g. `[::]:443`) declares it, nginx refuses to start with `duplicate listen options`.
Only the *first* server block for a given port needs `ipv6only=on`; subsequent ones for the same port just need
`listen [::]:443 ssl;`.

## 2. Certificate issuance

Certbot runs on the host (not containerized). The webroot it writes ACME challenge files to must be the exact same
host path that's bind-mounted into the nginx container at `/var/www/certbot` - i.e. whatever `CERTBOT_WEBROOT_DIR`
resolves to in `.env` (`docker-compose.yml`, `climweb_nginx_prod` volumes). If that env var isn't set, it silently
falls back to the relative default `./deploy/certbot/www`, which is a *different* directory from whatever path an
existing cert's `webroot_path` was issued against - certbot then writes files nginx never sees, and the CA gets a
404 on the challenge URL with no indication of the actual mismatch. Confirm the real, currently-mounted path with:

```bash
docker inspect climweb_nginx_prod --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' | grep certbot
```

**Gotcha - stale renewal hooks after a deployment migration:** each domain's `/etc/letsencrypt/renewal/<domain>.conf`
records a `renew_hook` that reloads nginx after a successful renewal, referencing a specific container name. If the
deployment is later migrated to a different Compose setup (as happened here, replacing an older `cms_nginx`
container with `climweb_nginx_prod`), old renewal configs keep the stale container name. The certificate still
renews fine, but the hook fails to reload nginx, so the running server keeps serving the old certificate until
someone notices. Check and fix on any deployment migration:

```bash
grep renew_hook /etc/letsencrypt/renewal/*.conf
sudo sed -i 's/<old_container_name>/<new_container_name>/' /etc/letsencrypt/renewal/<domain>.conf
sudo certbot renew --dry-run
```

## 3. Wagtail Site

In Wagtail Admin under **Settings > Sites**, add a Site with:

- **Hostname**: the exact subdomain, no scheme prefix, no trailing space/dot.
- **Port**: `443` (the externally visible port), even though nginx proxies to the app internally over plain HTTP.
- **Root page**: the section's top-level index page (e.g. `SummerSchoolIndexPage`).
- **Is default site**: unchecked - only the main site should have this set.

This does not move the page in the tree. The section's index page stays reachable at its original path under the
default site *and* becomes reachable at `/` on the new subdomain simultaneously - both routes resolve through the
same page-tree object.

## 4. Gotcha: `get_meta_description()` / `get_meta_image()` self-reference

Several page types (`SummerSchoolIndexPage`, and the same pattern in `contact`, `feedback`, `data_request`,
`events`, `email_subscription`) fall back to "the current site's homepage description/image" when they don't have
their own, via `climweb.base.seo_utils.get_homepage_meta_description`/`get_homepage_meta_image`, which resolve
`self.get_site().root_page.specific`.

That's safe when the page is a *child* of its site's homepage. It becomes an infinite recursion the moment the page
*is* its site's root page (exactly what step 3 does) - `get_site().root_page` resolves back to `self`, so the
method calls itself forever until Python hits `RecursionError`, surfacing as a 500.

`SummerSchoolIndexPage.get_meta_description()`/`get_meta_image()` were patched to skip the homepage fallback when
`self.get_site().root_page_id == self.pk`. The other five page types still have the same landmine - they're not
broken today only because none of them are currently assigned as a Site's root page. Apply the same guard to
whichever page type is promoted to a Site root next.

## 5. Gotcha: stale full-page cache after fixing routing

Climweb uses `wagtail-cache` (`WAGTAIL_CACHE = True` in production) for full-page caching, keyed by the request's
absolute URI (scheme + host + path). If a hostname ever served a 200 response *before* its Site routing was
correctly configured (e.g. during initial rollout, before the Wagtail Site above existed), that response gets
cached under the new subdomain's URL and keeps being served afterward - even after the Site is fixed - since the
cached response short-circuits before Wagtail's routing ever runs again. Clear it after any routing fix:

```bash
docker exec climweb_prod python /climweb/web/src/climweb/manage.py clear_wagtail_cache
```

No container restart or `collectstatic` is needed for this - the cache is Redis-backed and shared across all
gunicorn workers, so a clear takes effect immediately.
