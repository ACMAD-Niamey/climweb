# Product subscriptions and notifications roadmap

## Implemented foundation

- Store subscribers, consent metadata, confirmation state and product-family preferences in ClimWeb/PostgreSQL.
- Provide public subscribe, double-opt-in confirmation, preference-management and unsubscribe routes.
- Send through Django's email backend, allowing production to use Mailgun SMTP without coupling application data to Mailgun.
- Create notification events only after scheduled automatic importer commands complete successfully.
- Deduplicate automatic notifications by imported source record.
- Exclude preview and dashboard historical-import runs from automatic notifications.
- Provide an explicit **Notify subscribers about latest product** action on every importer page.
- Record per-subscriber delivery status and show recent notification history on the importer dashboard.
- Provide a dedicated **Email Subscribers** dashboard with subscriber totals,
  search, status and product filters, consent dates, selected products, sent
  counts, last-notified dates and recent notification activity.

## Phase 2 — production email delivery

1. Create and verify an ACMAD sending subdomain in Mailgun, for example `mail.acmad.org`.
2. Publish SPF, DKIM and DMARC records.
3. Configure the existing SMTP environment variables for web, worker and Beat containers.
4. Set `DEFAULT_FROM_EMAIL` to a monitored ACMAD sender address.
5. Run confirmation and product-notification delivery tests against a small authorised pilot list.

Example production values (replace the region, username and password with the
values shown in the verified Mailgun domain):

```dotenv
SMTP_EMAIL_HOST=smtp.eu.mailgun.org
SMTP_EMAIL_PORT=587
SMTP_EMAIL_USE_TLS=True
SMTP_EMAIL_HOST_USER=postmaster@mail.acmad.org
SMTP_EMAIL_HOST_PASSWORD=<mailgun-smtp-password>
DEFAULT_FROM_EMAIL=ACMAD Product Alerts <products@mail.acmad.org>
```

These variables are already passed to the web and Celery containers by
`docker-compose.yml`. The subscriber list and consent evidence remain in the
ClimWeb database; Mailgun is only the delivery transport.

## Phase 3 — operational controls

- Add CSV export for authorised subscriber-list administration.
- Add per-family notification enable/disable controls and configurable email subject/introduction text.
- Add a test-notification action and retry control for failed deliveries.
- Add Mailgun webhook handling for delivered, bounced, complained and unsubscribed events.
- Automatically suppress bounced and complaint addresses locally.
- Add rate limiting and batching appropriate to the provider plan.

## Phase 4 — digest delivery

- Add immediate, daily and weekly frequency preferences.
- Default high-frequency products such as rainfall and nowcasting to a digest.
- Combine multiple files from the same product issue into one message.
- Add localized templates for ACMAD's supported languages.

## Phase 5 — governance and reporting

- Add privacy-policy versioning and consent evidence export.
- Add subscriber data export and deletion workflows.
- Add notification engagement and deliverability reporting.
- Establish retention rules for delivery logs and inactive subscribers.
- Document provider failover and migration procedures.

## Notification safety rules

- Automatic notifications originate only from scheduled automatic imports.
- Manual historical imports and previews never notify subscribers automatically.
- The dashboard manual action always targets the latest successful file by issue date.
- One automatic notification event is allowed per source-import record.
- Only confirmed, active subscribers with a matching product preference are selected.
