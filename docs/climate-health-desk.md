# Climate and Health Desk

The Climate and Health Desk is a dedicated Wagtail Site served by the existing
ClimWeb application. It reuses ACMAD content instead of duplicating it.

## Bootstrap

Run migrations, then create the page tree and hostname mapping:

```bash
python manage.py migrate
python manage.py bootstrap_climate_health_desk --hostname climatehealthdesk.example.org
```

The command is idempotent. It creates the homepage, Products, Publications,
Platforms, Events, and Action Plan & Policies pages, as well as the Wagtail
`Site` record.

## Content workflow

- Assign the **Climate and Health** service to products, publications and events.
- Add existing GIS Applications to the homepage's **Existing platforms shown by
  the Health Desk** panel.
- Publications with a Climate and Health category and a type containing Policy,
  Strategy or Action Plan appear automatically on the policy page.
- Detail links use the existing canonical page on the main website.

## Web server

Add the real hostname to DNS and the TLS certificate, then add an HTTPS server
block equivalent to the existing `nrcc.acmad.org` block. It must proxy to
`climweb_prod:8000` and preserve the incoming `Host` header so Wagtail can select
the Health Desk `Site` record.
