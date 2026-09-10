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

## Adding another hostname later (e.g. `dev.acmad.org`)

1. Point its `A` record at the server; wait for `dig +short dev.acmad.org
   @8.8.8.8` to return the IP.
2. Re-run the `certonly … --expand` command above with the extra `-d
   dev.acmad.org`.
3. Add its `server` block to the active nginx config (it uses the same
   `include /etc/nginx/ssl/ssl.conf;`).
4. `nginx -t && nginx -s reload`.

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
