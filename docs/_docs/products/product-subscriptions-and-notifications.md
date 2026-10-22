# Product Subscriptions and Email Notifications

## Purpose and scope

The product subscription feature lets visitors select the ACMAD product families they want to follow and receive an
email when a qualifying product is imported. Subscriber records, consent evidence, preferences, notification events,
and delivery results are stored in ClimWeb's PostgreSQL database. The configured email provider, such as Mailgun, is
used only as the SMTP delivery service.

This guide covers:

- the public subscription and preference-management flow;
- the **Email Subscribers** dashboard;
- per-product notification controls on **Product Imports** pages;
- automatic and manual notification rules;
- SMTP and Mailgun deployment;
- testing, monitoring, privacy, and troubleshooting; and
- known limitations of the current implementation.

For importer operation, see [Product Importer Feature](product-importer-feature.md). For the remaining notification
roadmap, see `docs/product-subscription-roadmap.md`.

## Current implementation at a glance

| Capability | Current behavior |
| --- | --- |
| Subscriber storage | Stored locally in PostgreSQL; one record per normalized email address |
| Public entry point | `/subscribe/` |
| Legacy entry point | `/products/subscribe/` redirects to `/subscribe/` |
| Product selection | Product families are generated from active importer definitions |
| Consent evidence | Consent time, IP address, user agent, and preference selections are stored |
| Confirmation behavior | The normal public flow activates the subscriber immediately and queues a welcome email |
| Preference management | Tokenized link included in emails; email address is read-only |
| Unsubscribe | Tokenized confirmation page and dashboard action |
| Automatic notification | Runs after a successful scheduled automatic import, subject to the latest-product safety rule |
| Historical/manual import | Does not automatically notify subscribers |
| Manual notification | An administrator can notify subscribers about the latest successfully imported file |
| Recipient selection | Active subscribers whose preferences include the product family |
| Delivery transport | Django email backend; production uses SMTP |
| Activity tracking | Event-level recipient/sent/failed totals and per-subscriber delivery records |

## How the feature is connected

```text
Public /subscribe/ page
    -> subscriber + consent + product preferences in PostgreSQL
    -> welcome email queued through Celery

Scheduled automatic product import
    -> successful ProductSourceImport provenance record
    -> latest-product and deduplication checks
    -> ProductNotificationEvent
    -> one ProductNotificationDelivery per matching active subscriber
    -> SMTP provider

Product Imports dashboard
    -> product notification configuration
    -> manual latest-product notification
    -> recent event totals

Email Subscribers dashboard
    -> subscriber search/filter/export/status actions
    -> cross-product notification activity
```

The web application accepts subscription requests and dashboard actions. A Celery worker sends welcome and product
emails. Celery Beat runs the automatic product-import schedules that can create automatic notification events.

## Public subscription page

### Public URLs

- `/subscribe/` is the canonical subscription URL.
- `/products/subscribe/` is retained as a temporary redirect for old links.
- Preference and unsubscribe URLs contain a private UUID token and are generated separately for each subscriber.

Do not publish, log unnecessarily, or share a subscriber's preference or unsubscribe URL. Possession of the token is
sufficient to manage that subscriber's preferences or unsubscribe the address.

### Creating or editing the page in Wagtail

The site supports a single **Product Subscription Page**. Create it directly under the Home page and publish it with the
slug `subscribe`. This gives it the canonical `/subscribe/` URL. Although the model also technically permits the page
under Product Index, do not place it there: `/products/subscribe/` is reserved as the legacy redirect and using that URL
for the page would create conflicting navigation. When a live Product Subscription Page exists, the `/subscribe/` view
redirects to that page so its editable introduction, metadata, form fields, and existing site styling are used.

Recommended form fields are:

| Clean name | Suggested label | Type | Required | Storage |
| --- | --- | --- | --- | --- |
| `name` | Name | Single-line text | No | Subscriber record |
| `email` | Email | Email | Yes | Subscriber record and unique identifier |
| `sector` | Sector | Dropdown | No | Subscriber record |
| `organization_type` | Type of Organisation | Dropdown | No | Subscriber record |
| `organization_name` | Name of Organisation | Single-line text | No | Subscriber record |

The page injects **Products** and the consent checkbox automatically. Do not create duplicate versions of those two
fields in the form builder. Additional editorial fields are stored in the subscriber's `extra_data` record.

Use the canonical clean names above when a field should populate its dedicated subscriber column. A differently named
field can still be retained as extra data, but it will not appear in the dedicated dashboard fields.

The page's **From address**, **To address**, and **Subject** fields belong to Wagtail's general form-submission feature.
They do not replace the global SMTP settings or the per-product notification subject described later in this guide.

### Product and organization choices

The Products list comes from non-archived importer definitions, so a new active importer automatically becomes
available as a subscription choice. Retiring or archiving an importer removes it from new forms; existing preference
records remain in the database until they are changed or removed.

The static fallback form's built-in sector choices include agriculture, aviation, marine, media, environment, tourism, security, civil
protection, telecommunication, health, banking and finance, research, water and sanitation, and others. Organization
types include public sector, intergovernmental organization, private sector, academic/research, media, youth,
donor/finance institutions, NGO, and others. When the editable Wagtail page is used, configure its Sector and Type of
Organisation dropdowns with the same approved choices.

### Current subscriber journey

1. The visitor enters an email address and optional identity/organization details.
2. The visitor selects one or more product families and accepts the consent checkbox.
3. The email address is normalized to lowercase.
4. ClimWeb creates or updates the local subscriber, replaces the product preferences, records consent metadata, and
   sets the status to **Active**.
5. A Celery task sends the welcome email with preference-management and unsubscribe links.

Submitting an existing email updates that subscriber's details and replaces the previous product selections. It does
not create a duplicate subscriber.

### Confirmation policy

The current public flow is immediate opt-in: `confirmed_at` is set during form submission and the outgoing message is a
welcome email. A confirmation-token endpoint and **Pending** status exist in the data model, but the normal public flow
does not currently require the user to click a confirmation link before becoming active.

If ACMAD policy requires double opt-in, treat that as a code change: new subscribers should remain **Pending**, the
first email should contain the confirmation URL, and activation should happen only after the confirmation token is
visited. Do not describe the present implementation as double opt-in in privacy notices.

### Managing preferences and unsubscribing

Every welcome and product notification email includes:

- **Manage preferences**, which opens the subscriber's tokenized form, keeps the email address read-only, and allows
  product and profile changes; and
- **Unsubscribe**, which opens a confirmation page and changes the local status to **Unsubscribed** after submission.

Saving preferences reactivates an unsubscribed subscriber. This is appropriate only when the subscriber deliberately
uses their private preference link and submits the form.

## Email Subscribers dashboard

Sign in to Wagtail and select **Email Subscribers**. Access is restricted to superusers and users allowed to access the
Wagtail administration area.

### Summary and filters

The dashboard shows totals for:

- all subscribers;
- active;
- pending confirmation;
- unsubscribed; and
- bounced.

Administrators can search by name or email and filter by subscriber status or product family. The subscriber table
shows contact/organization details, selected products, confirmation date, sent-email count, last-notified time, and
available actions. Subscriber results are paginated in groups of 50.

### Exporting subscribers

Select **Export CSV** to export the current filtered result set. The export includes email, name, status, confirmation
and unsubscribe dates, sector, organization type/name, and preferred product families. Spreadsheet-formula prefixes
are escaped before export.

The CSV contains personal data. Store it only in an approved location, restrict access, and delete working copies when
they are no longer required.

### Dashboard actions

- **Unsubscribe** changes the local subscriber status and prevents future delivery.
- **Resend** is displayed for pending subscribers.

Current limitation: frontend subscriptions are normally created as Active, so Pending records generally come from
legacy data or manual administration. The dashboard displays **Resend** for Pending records, but the current resend view
sends only when the subscriber is Active. Therefore the Pending resend button does not currently deliver a message and
must be fixed before it is used as part of a double-opt-in workflow.

### Recent notification activity

The lower dashboard table shows the most recent events across products:

- product and issue date;
- trigger: **Automatic import** or **Dashboard action**;
- event status: Queued, Sending, Sent, or Failed;
- recipient, sent, and failed counts; and
- creation time.

An event marked **Sent** can legitimately have zero recipients when no active subscriber selected that product.

## Per-product notification management

Open **Product Imports**, select a product family, and use the notification sections on its individual importer page.

### Latest imported file and manual notification

The **Latest imported file** panel selects the newest successful file by issue date. Select **Notify subscribers about
latest product** and confirm the browser prompt to queue a dashboard-triggered notification.

The manual action:

- selects the latest successful provenance record, not the most recently created database row;
- sends only to active subscribers who selected that family;
- records the requesting administrator;
- reuses an existing event for the same product file, preventing an already-sent latest file from being broadcast
  repeatedly; and
- shows a warning when there is no successful imported file or notifications are disabled.

Do not use a historical import to try to select the notification file. First verify the issue date in **Latest imported
file**, then use the explicit notification button.

### Notification settings

Each product importer page has a **Notification settings** form:

- **Enable notifications for this product family** controls both automatic and dashboard-triggered notifications.
- **Custom Email Subject** overrides the standard subject. Supported variables are `{{ product_label }}` and
  `{{ date }}`.
- **Email Introduction Text** adds product-specific text near the top of the email.

The default subject is:

```text
New ACMAD product: <product label> — <issue date>
```

Test customized subjects and introductions with a small authorized subscriber list before enabling automatic delivery.
Do not place credentials, private data, or unsupported template expressions in these fields.

### Recent product notifications

The importer page also shows the ten most recent events for that product family, including issue date, trigger, status,
recipient count, sent count, failed count, and creation time.

## Automatic notification rules

Automatic notification is coupled to the scheduled importer wrapper, not to every way a product can be created.

The intended safety rules are:

1. The product's automatic importer must be enabled and run through Celery Beat.
2. The import command must finish successfully.
3. The notification setting for the product family must be enabled.
4. The newest successful source is selected by `source_published_date`, then import time and primary key.
5. That newest source must have been touched by the current automatic run.
6. A source-specific automatic key prevents a second automatic event for the same imported file.
7. Only active subscribers with a matching product preference receive the event.

Manual historical imports and previews do not automatically notify subscribers. Importing an old archive record must
not generate a notification merely because its database row was updated.

The latest-only safeguard is implemented by commit `eddf2666` on the `email-subscriptions` branch. Before deploying
notification code from another branch, confirm that this commit is included. Otherwise one automatic run that touches
multiple historical records can create notifications for those older issue dates.

## Email content and branding

Emails are sent as multipart messages with plain-text and HTML alternatives. The templates use:

- the default Wagtail Site name and public root URL;
- the organization's logo, when configured;
- the default theme colors;
- configured social-media links;
- product issue date, filename, link, description, and validity dates when available; and
- preference and unsubscribe links.

Ensure **Settings → Sites** contains the correct production hostname and port. Public product, preference, logo, and
unsubscribe URLs are built from the default Wagtail Site. An incorrect Site record can produce localhost or wrong-domain
links even when SMTP delivery succeeds.

## SMTP and Mailgun production setup

### Required infrastructure

For Mailgun or another SMTP provider:

1. Create a dedicated sending subdomain, for example `mail.acmad.org`.
2. Verify the domain with the provider.
3. Publish the provider's SPF and DKIM records.
4. Publish an ACMAD DMARC policy and reporting address.
5. Create SMTP credentials for the application.
6. Use a monitored From address on the verified domain.
7. Keep credentials in the server environment or secret manager, never in Git.

### Docker Compose environment variables

Set the following values in the deployment `.env` file. Use the SMTP hostname and region shown in the provider account:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
SMTP_EMAIL_HOST=smtp.eu.mailgun.org
SMTP_EMAIL_PORT=587
SMTP_EMAIL_USE_TLS=True
SMTP_EMAIL_HOST_USER=postmaster@mail.acmad.org
SMTP_EMAIL_HOST_PASSWORD=<secret-from-provider>
DEFAULT_FROM_EMAIL=ACMAD Product Alerts <products@mail.acmad.org>
CMS_BASE_URL=https://new.acmad.org
```

`docker-compose.yml` maps the host variables prefixed with `SMTP_` to Django's container variables (`EMAIL_HOST`,
`EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, and `EMAIL_HOST_PASSWORD`). If Django is run without Docker Compose,
configure the container-side `EMAIL_*` names directly.

After changing SMTP values, recreate the web, worker, and Beat services so all processes receive the same environment:

```bash
docker compose --profile prod up -d --force-recreate \
  climweb_prod climweb_celery_worker_prod climweb_celery_beat_prod
```

The default development backend writes messages to the console instead of delivering them. Seeing email text in logs
but nothing in an inbox usually means the console backend is still active.

### Provider pilot

Before enabling notifications broadly:

1. Create two or three authorized test subscribers using different email providers.
2. Select one low-frequency product family.
3. Confirm welcome delivery and that all links use the production domain.
4. Use **Notify subscribers about latest product** once.
5. Compare event recipient/sent/failed totals with the test list.
6. Check provider delivery logs, spam placement, SPF, DKIM, and DMARC alignment.
7. Test preferences and unsubscribe, then confirm that the address is excluded from the next send.

## Deployment checklist

- [ ] The subscription and notification migrations are applied, including product migrations `0050` through `0054`.
- [ ] A live Product Subscription Page exists at `/subscribe/` and contains the canonical form fields.
- [ ] The default Wagtail Site uses the production hostname and HTTPS port settings.
- [ ] Redis, the Celery worker, and Celery Beat are healthy.
- [ ] The deployed notification code includes the latest-only safeguard from commit `eddf2666`.
- [ ] SMTP variables are present in the web, worker, and Beat containers.
- [ ] The sending domain passes provider verification, SPF, DKIM, and DMARC checks.
- [ ] Product notification settings have been reviewed family by family.
- [ ] A small pilot has verified welcome, product, preference, and unsubscribe flows.
- [ ] Subscriber CSV access and storage rules have been agreed.
- [ ] Database backups include subscriber, consent, event, and delivery records.

## Testing

Run the focused automated tests in the development container:

```bash
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py test \
  climweb.pages.products.tests.test_product_notifications --verbosity=2
```

The focused suite covers the canonical subscription URL, local subscriber storage, preferences, confirmation and
unsubscribe status changes, automatic-event deduplication, active/matching recipient selection, dashboard-triggered
latest notification, dashboard access, and filters. On a branch containing `eddf2666`, it also verifies that an
automatic run selects only the latest touched source and ignores historical backfills.

Automated tests use an in-memory email backend. They do not prove that production SMTP credentials, DNS records, or
provider reputation are correct, so the provider pilot remains mandatory.

## Troubleshooting

### A subscription succeeds but no welcome email arrives

1. Confirm the subscriber appears as Active in **Email Subscribers**.
2. Confirm the Celery worker is running; welcome messages are queued tasks.
3. Confirm production is using the SMTP backend rather than the console backend.
4. Check worker logs for authentication, TLS, DNS, connection, sender-domain, or provider rejection errors.
5. Confirm the From address belongs to the verified sending domain.

### A notification remains Queued

The event has been created but the Celery worker has not completed it. Check Redis connectivity and worker health, then
restart/recreate the worker with the same environment as the web service.

### An event is Sent with zero recipients

The event completed successfully, but no Active subscriber selected that product family. Check the product filter in
**Email Subscribers** and verify the expected subscribers' preferences and statuses.

### Active subscribers do not receive a product

- Confirm notifications are enabled on that product's importer page.
- Confirm the subscriber selected the exact product family.
- Check the event's recipient, sent, and failed totals.
- Check the provider delivery log and spam/bounce result.
- Verify that the product has a successful `ProductSourceImport` record.

### A historical issue generates an automatic email

- Verify that the deployed code contains commit `eddf2666`.
- Recreate the Celery worker; a running worker can retain code from the previous image.
- Check the imported records' `source_published_date` values. A malformed date can make an old product appear latest.
- Keep historical imports manual; do not use the automatic schedule for bulk backfills.

### The manual button says no successful file exists

Confirm that the importer has at least one provenance record with status **Imported** and a valid issue date. Also check
whether notifications are disabled for the family; the current user-facing warning is shared by both conditions.

### Email links use localhost or the wrong domain

Correct the default Wagtail Site hostname/port and verify `CMS_BASE_URL`. Recreate web and worker services, then send a
new pilot email.

### SMTP works from the web container but not for notifications

The Celery worker sends the actual welcome and product messages. Confirm the SMTP variables exist inside the worker
container and recreate the worker after any `.env` change.

### Some deliveries fail while others succeed

The event is marked Failed if any recipient delivery fails; successful per-subscriber deliveries remain recorded and
are skipped when the same event is retried. Use worker/provider logs to resolve the failed addresses. Automated bounce
and complaint webhooks are not yet implemented.

## Data protection and operational controls

- Subscriber and consent records belong to ACMAD and remain in PostgreSQL.
- Mailgun or another SMTP provider receives addresses only to deliver messages; it is not the system of record.
- Restrict dashboard and CSV export access to authorized staff.
- Treat preference and unsubscribe tokens as personal secrets.
- Preserve consent evidence and unsubscribe status during backups/restores.
- Do not reactivate or edit a subscriber without a documented user request or lawful operational basis.
- Establish retention periods for inactive subscribers and delivery logs.
- Define a process for data access, correction, deletion, bounce, and complaint requests.

## Known limitations and recommended next work

The following work remains outside the current foundation:

- enforce true double opt-in if required by ACMAD policy;
- correct and test the pending-subscriber resend workflow;
- add a dedicated test-email action that does not create a product event;
- add an administrator retry action for failed notification events/deliveries;
- process provider webhooks for delivered, bounced, complained, and unsubscribed events;
- automatically suppress bounced and complaint addresses;
- add delivery batching/rate limits and immediate/daily/weekly digest preferences;
- add localized email templates;
- add consent export, data-deletion, retention, and deliverability reporting; and
- define provider failover and incident-response procedures.

## Implementation reference

| Area | Location |
| --- | --- |
| Subscriber, preference, configuration, event, delivery, and page models | `climweb/src/climweb/pages/products/models.py` |
| Public and dashboard views | `climweb/src/climweb/pages/products/views.py` |
| Public routes | `climweb/src/climweb/pages/products/urls.py` |
| Wagtail dashboard routes and menu entries | `climweb/src/climweb/pages/products/wagtail_hooks.py` |
| Notification selection and delivery | `climweb/src/climweb/pages/products/product_notifications.py` |
| Celery tasks and automatic-import wrapper | `climweb/src/climweb/pages/products/tasks.py` |
| Subscription and importer templates | `climweb/src/climweb/pages/products/templates/products/` |
| Focused tests | `climweb/src/climweb/pages/products/tests/test_product_notifications.py` |
| Docker email variable mapping | `docker-compose.yml` |
| Django email settings | `climweb/src/climweb/config/settings/base.py`, `dev.py`, and `production.py` |
