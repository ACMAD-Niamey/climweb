# TLS Certificates

How ACMAD's ClimWeb instance gets and keeps its HTTPS certificate. This is
host-managed and **not** touched by the CI/CD pipeline (see
[deployment.md](deployment.md)).

## How it's wired

- **Certbot runs on the host**, not in a container (`apt install certbot`).
- It uses the **webroot** authenticator: it writes an HTTP-01 challenge file
  into a directory, Let's Encrypt fetches it over plain port 80, nginx serves
  it.
- That directory is `/var/www/certbot` on the host (`CERTBOT_WEBROOT_DIR` in
  `.env`), bind-mounted **read-only** into `climweb_nginx_prod` at
  `/var/www/certbot` (see `docker-compose.yml`). Every nginx config serves it:

  ```nginx
  location ^~ /.well-known/acme-challenge/ {
      root /var/www/certbot;
      try_files $uri =404;
  }
  ```

- Issued certs live in `/etc/letsencrypt/` on the host, bind-mounted read-only
  into the container at `/etc/letsencrypt` (`LETSENCRYPT_DIR` in `.env` — note
  the compose variable is `LETSENCRYPT_DIR`, not `LETSENCRYPT_VOLUME`).
- nginx reads the cert **path** from `deploy/nginx/ssl/ssl.conf` (git-ignored,
  one per host; `ssl.conf.sample` is the template), pulled into each `server`
  block with `include /etc/nginx/ssl/ssl.conf;`. Change the path in one place,
  not in every block.

## One SAN certificate for every hostname

ACMAD uses a **single certificate** covering all hostnames as SANs, with the
lineage named `acmad.org`:

| lineage | domains | path |
| ------- | ------- | ---- |
| `acmad.org` | `acmad.org`, `www.acmad.org`, `new.acmad.org`, `summerschool.acmad.org` | `/etc/letsencrypt/live/acmad.org/` |

`deploy/nginx/ssl/ssl.conf` therefore contains:

```nginx
ssl_certificate     /etc/letsencrypt/live/acmad.org/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/acmad.org/privkey.pem;
```

## Issuing / expanding the certificate

Prerequisite: **every domain must already resolve to this server** (`dig
+short <domain> @8.8.8.8` returns the host IP) and nginx must be up serving the
challenge path on port 80. Delete any stale `AAAA` record first — Let's Encrypt
prefers IPv6, and a wrong `AAAA` fails validation even with a correct `A`.

First issue, or add a domain to the existing cert (`--expand`):

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  --cert-name acmad.org --expand \
  -d acmad.org -d www.acmad.org -d new.acmad.org -d summerschool.acmad.org \
  --deploy-hook "docker exec climweb_nginx_prod nginx -s reload"
```

- `--cert-name acmad.org` keeps the lineage (and path) stable no matter which
  `-d` comes first.
- `--expand` adds new `-d` names to the existing lineage; harmless if the set
  is unchanged.
- `--deploy-hook` is stored in the renewal config and runs after every
  successful renewal — this is what reloads nginx to pick up the new cert.

After issuing, if `ssl.conf` doesn't already point at
`/etc/letsencrypt/live/acmad.org/`, update it and reload:

```bash
docker exec climweb_nginx_prod nginx -t && docker exec climweb_nginx_prod nginx -s reload
```

## Renewal

Renewal is automatic. On Ubuntu it's a **systemd timer** (`certbot.timer`),
which runs `certbot renew` twice a day; a cert only actually renews inside 30
days of expiry, otherwise it's a no-op. `certbot renew` re-reads each
`/etc/letsencrypt/renewal/*.conf` and reuses the authenticator, webroot and
deploy-hook recorded there.

Check it:

```bash
# is the timer active and when does it next run?
systemctl list-timers '*certbot*' --all
systemctl status certbot.timer

# what will actually happen, end to end, without touching the real cert
sudo certbot renew --dry-run

# the renewal config for our cert
sudo cat /etc/letsencrypt/renewal/acmad.org.conf
```

`acmad.org.conf` must have:

```ini
[renewalparams]
authenticator = webroot
webroot_path = /var/www/certbot
renew_hook = docker exec climweb_nginx_prod nginx -s reload
server = https://acme-v02.api.letsencrypt.org/directory
```

Two things that silently break renewal:

- **`webroot_path` not `/var/www/certbot`.** If it points anywhere else,
  certbot writes challenge files nginx never serves and the CA gets a 404.
  Confirm the mounted path: `docker inspect climweb_nginx_prod --format
  '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' | grep
  certbot`.
- **A stale `renew_hook` container name.** After a deployment migration the
  hook can still name an old container (`cms_nginx`, …). The cert renews but
  nginx keeps serving the old one. Fix:
  `sudo sed -i 's/<old_name>/climweb_nginx_prod/' /etc/letsencrypt/renewal/acmad.org.conf`.

## Adding a new hostname / subdomain

Full checklist of everything that has to change to serve a new hostname (e.g.
`dev.acmad.org`, `data.acmad.org`). Steps 1-4 are always needed; 5-6 depend on
what the hostname is for.

### 1. DNS

Add an `A` record for the hostname pointing at the server IP. If you use a
wildcard already (`*.acmad.org`), an explicit record still overrides it and is
clearer. Do **not** add an `AAAA` unless the box has working IPv6.

```bash
dig +short dev.acmad.org @8.8.8.8      # wait until this returns the server IP
dig +short AAAA dev.acmad.org @8.8.8.8 # must be empty (or a real, served IPv6)
```

### 2. Certificate — add it as a SAN on the `acmad.org` cert

Re-run the issuing command with the extra `-d`, keeping every existing name:

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  --cert-name acmad.org --expand \
  -d acmad.org -d www.acmad.org -d new.acmad.org -d summerschool.acmad.org \
  -d dev.acmad.org \
  --deploy-hook "docker exec climweb_nginx_prod nginx -s reload"
```

The live path (`/etc/letsencrypt/live/acmad.org/`) does not change, so
`deploy/nginx/ssl/ssl.conf` needs no edit. The deploy-hook reloads nginx with
the new cert automatically.

### 3. nginx — add a `server` block

Edit the **active** config (whichever `NGINX_CONFIG_PROD` points at, currently
`deploy/nginx/nginx.prod.acmad.ssl.conf`):

- add the hostname to the **port-80** `server_name` line (so its ACME challenge
  and HTTP→HTTPS redirect work);
- add an HTTPS `server` block for it. Copy an existing one and change only
  `server_name`. It reuses `include /etc/nginx/ssl/ssl.conf;` — no cert paths
  to type. A block either **serves** the app (`location / { proxy_pass … }`,
  like `acmad.org`) or **redirects** (`return 301 https://acmad.org$request_uri;`,
  like `www`).
- only the **first** `listen 443` block in the file may carry `ipv6only=on` —
  new blocks use plain `listen [::]:443 ssl;`.

```bash
docker exec climweb_nginx_prod nginx -t    # no "conflicting server name" / "duplicate listen"
docker exec climweb_nginx_prod nginx -s reload
```

Commit the config change to the repo (`deploy/nginx/…`) so it isn't lost on the
next `git pull` / redeploy.

### 4. Django — allow the host

In `.env` on the host, add the hostname to **both**:

```
ALLOWED_HOSTS=…,dev.acmad.org
CSRF_TRUSTED_ORIGINS=…,https://dev.acmad.org
```

No spaces, no trailing `#` comments — django-environ splits on `,`. Then
recreate the app container (a restart does **not** re-read `.env`):

```bash
docker compose --profile prod up -d --force-recreate climweb_prod
```

A 400 on the new hostname means this step didn't take — check
`docker compose --profile prod exec climweb_prod python …/manage.py shell -c
"from django.conf import settings; print(settings.ALLOWED_HOSTS)"`.

### 5. If it serves a section of the site on its own subdomain

(Like `summerschool.acmad.org`.) Add a Wagtail **Site** record — Settings →
Sites — with the hostname, port `443`, and the section's index page as the root
page. Full details and gotchas in
[subdomain-deployment.md](subdomain-deployment.md).

### 6. If it's a separate deployment (own container)

(Like a future `dev.acmad.org` preview.) The nginx block proxies to a different
upstream (`set $upstream climweb_dev:8000;`), and that container/stack has to
be running. This is more involved — see the notes in the memory / PR history
for why the `/dev` path-mount was shelved.

### Retiring a hostname

Reverse of the above: remove its `server` block and its entry on the port-80
`server_name`, drop it from `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`, remove the
DNS record. To drop it from the cert, re-run `certonly` **without `--expand`**
and list only the names to keep — certbot detects the smaller set and prompts
to remove the rest:

```bash
sudo certbot certonly --webroot -w /var/www/certbot --cert-name acmad.org \
  -d acmad.org -d www.acmad.org -d summerschool.acmad.org \
  --deploy-hook "docker exec climweb_nginx_prod nginx -s reload"
```

Reload nginx, recreate `climweb_prod`. (Leaving the stale name on the cert is
harmless too — it just renews an unused SAN.)

## Removing an old standalone cert

If separate per-domain certs exist from before the SAN cert (check with
`sudo certbot certificates`), and **no** nginx config still references their
paths (`grep -rn 'live/<name>' deploy/nginx/`), delete them so they stop
renewing pointlessly:

```bash
sudo certbot delete --cert-name new.acmad.org
sudo certbot delete --cert-name summerschool.acmad.org
```

This only removes that lineage and its renewal config — SANs on the `acmad.org`
cert are untouched.

## Command cheat sheet

```bash
# what certs exist, their SANs, expiry, paths
sudo certbot certificates

# every renewal config (spot leftovers)
ls -la /etc/letsencrypt/renewal/
sudo grep -H -E 'renew_hook|webroot_path|authenticator' /etc/letsencrypt/renewal/*.conf

# dry-run renewal (safe)
sudo certbot renew --dry-run

# force a renewal now (only when you actually need it)
sudo certbot renew --force-renewal --cert-name acmad.org

# inspect the live cert nginx is serving
echo | openssl s_client -connect www.acmad.org:443 -servername www.acmad.org 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName

# is a domain reachable for validation?
dig +short acmad.org @8.8.8.8
dig +short AAAA acmad.org @8.8.8.8          # should be empty unless real IPv6
curl -sI http://acmad.org/.well-known/acme-challenge/ping   # 404 from nginx = good

# confirm the webroot + cert dir are mounted into nginx
docker inspect climweb_nginx_prod \
  --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' \
  | grep -E 'certbot|letsencrypt'

# reload nginx after any cert change
docker exec climweb_nginx_prod nginx -t && docker exec climweb_nginx_prod nginx -s reload

# certbot's own logs
sudo tail -n 50 /var/log/letsencrypt/letsencrypt.log
```
