# Configure Staff Google Drive

The staff workspace can use a Google service account to manage files inside an organization Shared Drive. Credentials
remain server-side and must be mounted read-only.

## Required configuration

Configure names in the deployment secret/environment system; never commit values or the JSON key:

```env
GOOGLE_DRIVE_ENABLED=True
GOOGLE_DRIVE_SERVICE_ACCOUNT_HOST_FILE=./secrets/acmad-drive-service-account.json
GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE=/run/secrets/acmad-drive-service-account.json
GOOGLE_DRIVE_SHARED_DRIVE_ID=<shared-drive-id>
GOOGLE_DRIVE_ROOT_FOLDER_ID=<folder-id-inside-that-shared-drive>
```

Add the service account's `client_email` as a **Content manager** member of the Shared Drive. Sharing only the root folder
is insufficient for Shared Drive operations.

## Security model

- Staff receive an application-managed personal folder beneath the configured root.
- Reviewers with `staff.review_staff_profiles` can browse the configured organization root and managed staff folders.
- Staff cannot create folders through the portal.
- Every list, upload, download, rename, move, and trash operation validates the configured root boundary server-side.
- Mutations and downloads are recorded in `StaffDriveAudit`.
- Up to 10 files can be uploaded per request, with a 50 MB per-file limit.
- Google Docs, Sheets, Slides, and Drawings are exported as DOCX, XLSX, PPTX, and PDF for portal downloads.

The service account must not have broader institutional Drive access than the application requires.

## Deployment

1. Create the service account under an institutionally owned Google Cloud/Workspace project.
2. Store its key in the approved host secret location.
3. Configure the Shared Drive and root folder IDs.
4. Grant the service account Content manager membership.
5. Recreate affected web and worker services so the mount/configuration is applied.
6. Apply migrations.
7. Run the health command.

Development-profile example:

```bash
docker compose --profile dev up -d --force-recreate climweb_dev climweb_celery_worker_dev
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py migrate --noinput
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py check_staff_drive
```

Use the corresponding production services only through the approved release procedure.

## Report synchronization

Activity-report attachments keep a protected local copy and synchronize to Drive through Celery. The local protected
copy remains the authoritative workspace download. Production web and worker services must share
`private_staff_reports_prod` so the worker can read pending files.

Failed synchronization is retried. Do not delete the local file or database record merely because a Drive upload failed.
Investigate credentials, membership, root boundary, file access, worker health, and retry state.

## Acceptance test

Using non-sensitive test data:

1. Run `check_staff_drive` successfully.
2. Open the staff Drive as a normal staff member and confirm scope is limited to the personal folder.
3. Upload, download, rename, and move a test file.
4. Confirm folder creation remains unavailable to normal staff.
5. Confirm an authorized reviewer can browse the configured organization root.
6. Submit a test activity-report attachment and observe successful asynchronous synchronization.
7. Confirm audit records for mutations/downloads.
8. Confirm an unrelated Drive/folder ID is rejected.
9. Trash test content through the supported workflow and record the result.

## Key rotation and offboarding

For rotation:

1. Create a replacement key through the institutional owner.
2. Deploy it without committing or logging its contents.
3. Recreate web/worker services.
4. Run the health and acceptance checks.
5. Revoke the old key and record the date/operator.

When ownership changes, transfer the Cloud project, Shared Drive, recovery contacts, billing, audit visibility, and
rotation responsibility—not just a downloaded JSON file.

## Backup and recovery

Back up the database and protected local report storage. Shared Drive is an external dependency and must have its own
retention/recovery policy. A recovery rehearsal should verify database mappings, local protected downloads, Drive folder
references, a synchronized report, and least-privilege access after restoration.

## Troubleshooting

- **Health check cannot authenticate:** verify the mounted path, JSON readability, enabled API, key status, and container
  recreation.
- **Shared Drive not found:** verify Drive ID and service-account membership.
- **Root folder rejected:** confirm it is inside the configured Shared Drive.
- **Staff sees too much:** disable Drive access immediately and review root/member permissions and reviewer permission.
- **Report remains pending/failed:** inspect worker logs, shared private volume, retry state, and Drive audit/error detail.
- **Download export fails:** confirm the Google-native type is supported and Drive API permissions remain valid.
