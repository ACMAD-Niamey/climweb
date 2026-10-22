# Configure Google Meet

ClimWeb can create a Google Calendar event with a unique Google Meet link for
online and hybrid events. After a visitor registers, ClimWeb sends the link to
the email address stored in that registration. The link is not displayed on the
public event page.

## Google Workspace setup

1. Create or select a project in Google Cloud Console.
2. Enable the **Google Calendar API**.
3. Create a service account and enable domain-wide delegation for it.
4. In Google Admin Console, open **Security → Access and data control → API
   controls → Manage domain-wide delegation**.
5. Add the service account's OAuth client ID with this scope:

   ```text
   https://www.googleapis.com/auth/calendar.events
   ```

6. Create a dedicated Workspace user, for example `events@example.org`. This
   account owns the generated Calendar events and Meet conferences.
7. Download the service-account JSON key and store it as a deployment secret.
   Never commit it to the repository or upload it through Wagtail.

## Deployment configuration

Mount the JSON key read-only into both the ClimWeb web container and Celery
worker container. Set the environment variable to its path inside the
container, for example:

```text
GOOGLE_MEET_SERVICE_ACCOUNT_FILE=/run/secrets/google-meet-service-account.json
```

The SMTP settings and Celery worker must also be operational because ClimWeb
sends participant links asynchronously and retries transient failures.

Run migrations after deploying the code:

```bash
python manage.py migrate
```

## Wagtail configuration

1. Open **Settings → Google Meet settings**.
2. Enable the integration.
3. Enter the dedicated Workspace organizer email.
4. Leave Calendar ID blank to use that user's primary calendar, or enter a
   writable calendar ID.
5. Configure the participant email subject and save.

## Create an online or hybrid event

1. Set **Attendance mode** to **Online** or **Hybrid**.
2. Set **Meeting Registration Integration Platform** to **Google Meet**.
3. Set both a start and end date/time.
4. Publish the event.

Publishing queues Calendar and Meet creation. Publishing a later schedule or
content change updates the same Calendar event instead of creating a duplicate.
Each successful registration queues one private participant email. Failed API
or email calls are retried and ultimately reported to the configured Django
administrators.
