# Staff portal Google Drive integration

The staff workspace uses a Google service account to manage files in an organization Shared Drive. Google credentials remain server-side and are mounted read-only into the web container.

## Required configuration

Set these values in `.env`:

```env
GOOGLE_DRIVE_ENABLED=True
GOOGLE_DRIVE_SERVICE_ACCOUNT_HOST_FILE=./secrets/acmad-drive-service-account.json
GOOGLE_DRIVE_SHARED_DRIVE_ID=<shared-drive-id>
GOOGLE_DRIVE_ROOT_FOLDER_ID=<folder-id-inside-that-shared-drive>
```

The compose configuration exposes the credential inside the container at `/run/secrets/acmad-drive-service-account.json`; do not commit the JSON key. Add the service account's `client_email` as a member of the Shared Drive with **Content manager** access. Sharing only the root folder is not sufficient for Shared Drive operations.

After changing configuration, recreate the web service and verify access:

```shell
docker compose --profile dev up -d --force-recreate climweb_dev
docker compose --profile dev exec -T climweb_dev python /climweb/web/src/climweb/manage.py migrate
docker compose --profile dev exec -T climweb_dev python /climweb/web/src/climweb/manage.py check_staff_drive
```

## Access model

- Staff members receive an app-managed personal folder below the configured root the first time they open Drive or upload an activity report attachment.
- Users with `staff.review_staff_profiles` can browse the configured organization root and all staff folders.
- Users cannot create folders through the portal. Manual uploads and activity report attachments are always placed in the uploader's dedicated staff folder.
- Every folder boundary is verified server-side before listing, upload, download, rename, move, or trash operations.
- Mutating actions and downloads are recorded in `StaffDriveAudit`.
- Uploaded files are limited to 50 MB each and 10 files per request.

Activity report attachments retain an authenticated private local copy and are synchronized to Drive by Celery. Failed synchronization is retried automatically. The production web and Celery worker services share the `private_staff_reports_prod` volume so the worker can read the protected attachment during synchronization.

Google-native Docs, Sheets, Slides, and Drawings are exported as DOCX, XLSX, PPTX, and PDF when downloaded through the portal.
