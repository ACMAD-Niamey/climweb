# Staff workspace

The staff workspace is ClimWeb's private area for staff profiles, professional
activity assignments, activity reports and organization files. It is separate
from the public **Our Team** page and from the Wagtail CMS, although approved
profile changes are published to the public page through Wagtail.

This guide covers day-to-day use, permissions and operational setup. Detailed
reference material is also available for [profile invitations and
self-service](staff-profile-portal.md) and the [Google Drive
integration](staff-google-drive.md).

## Entry points

| Area | Default path | Who can use it |
| --- | --- | --- |
| Staff sign-in | `/staff/login/` | Current staff with a linked, active account |
| Staff dashboard | `/staff/` | Current staff with a linked, active account |
| HR dashboard | `/staff/hr/` | Linked current staff with the profile-review permission |
| My Profile | `/staff/profile/` | Current staff with a linked, active account |
| Organization files | `/staff/files/` | Current staff; access scope depends on permission |
| Staff Profiles administration | `/cms-admin/staff-profiles/` | Wagtail users with the profile-review permission |

The paths assume that ClimWeb is installed at the root of the website. The
workspace pages are marked `noindex, nofollow` and require authentication.

## Roles and permissions

The workspace uses existing Django and Wagtail permissions rather than a
separate HR role.

| Capability | Staff member | Reviewer / HR | Superuser |
| --- | :---: | :---: | :---: |
| Edit and submit own public profile | Yes | Yes, for own linked profile | Yes, for own linked profile |
| View own activity assignments and reports | Yes | Yes | Yes |
| Use own Drive folder | Yes | Yes | Yes |
| Browse all staff Drive folders | No | Yes | Yes |
| Assign activities | No | Yes | Yes |
| Review activity reports | No | Yes | Yes |
| Review profile submissions | No | Yes | Yes |
| Add, edit, link, offboard or reactivate staff | No | No | Yes |
| Send invitations and bulk reminders | No | No | Yes |

Reviewer access is granted with the `staff.review_staff_profiles` permission
(**Can review staff profile submissions**). A reviewer also needs normal Wagtail
admin access. To approve public profile changes, the reviewer's Wagtail group
must have **Edit** and **Publish** permission on the relevant Our Team page.

The HR dashboard and its report-review pages are inside the staff workspace.
Consequently, an HR user must also be linked to a current staff profile. The
Wagtail **Staff Profiles** administration screen only requires reviewer access.

Profile-only accounts created by an invitation do not receive CMS, Django admin,
API, staff or superuser permissions. Do not grant CMS permissions to these
accounts as a shortcut for creating reviewers. Link the reviewer's existing
platform account instead.

## Staff member guide

### Activate an account and sign in

1. Open the invitation sent to the registered work email address.
2. Follow the link and choose a password. Invitation links are single-use and
   expire after 48 hours.
3. Sign in at `/staff/login/` using the work email address and password.

An existing platform account linked by an administrator keeps its existing
password and sign-in method. Local-password accounts can also use their
registered email at the staff sign-in page, even when their platform username is
different. External or SSO accounts continue to use their normal sign-in method.

Use **Forgot your password?** on the sign-in page when necessary. Password reset
messages are only sent for active, current staff accounts that support a local
password.

### Dashboard

The dashboard summarizes:

- active professional activity assignments;
- reports that are not started or remain in draft;
- reports approved by HR;
- the staff member's role, department and registered email; and
- Google Drive availability.

Assignments show their activity type, dates, organizer, location, status and
report deadline. Cancelled assignments cannot receive a report.

### Update the public profile

Open **My Profile** to propose changes to:

- biography;
- professional website;
- LinkedIn profile;
- GitHub profile;
- publications page; and
- portrait.

The biography is plain text; blank lines create separate paragraphs. Portraits
must be JPEG, PNG or WebP, no larger than 5 MB or 4096 × 4096 pixels. Uploaded
images are re-encoded as JPEG, stripped of metadata and reduced to a maximum of
1600 pixels.

Choose **Save draft** to continue later or **Submit for review** when the update
is ready. Neither action changes the public profile immediately. A submitted
update is locked until a reviewer approves it or requests changes. The profile
history shows the latest review result and reviewer comment.

Name, official job title, department, registered email and inclusion on the Our
Team page remain administrator-managed. The public email icon uses the linked
account's registered email address.

### Complete an activity report

1. Open **Activities & Reports** and select an assignment.
2. Enter the report title, summary, and key outcomes or follow-up actions.
3. Optionally attach as many as three supporting documents.
4. Choose **Save draft** to continue later or **Submit to HR** for review.

Supported attachments are PDF, Word, PowerPoint, OpenDocument Text and
OpenDocument Presentation files. Each attachment may be up to 10 MB. Report
attachments are served through an authenticated download endpoint and are not
public media files.

Submitted reports are locked while awaiting review. If HR requests changes, the
report becomes editable again and can be resubmitted. Approval marks the report
approved and the assignment completed.

When Drive is enabled, new report attachments are also synchronized to the staff
member's Drive folder in the background. The private local copy remains the
authoritative authenticated download source in the workspace.

### Work with organization files

Open **Drive** to browse the assigned personal folder. Staff can:

- upload up to 10 files per request, with a 50 MB limit per file;
- download files;
- rename files and folders;
- move items within the permitted folder tree; and
- move items to the Shared Drive trash.

The workspace creates the personal folder automatically the first time it is
needed. Staff cannot create new folders through the portal. Every operation is
checked on the server to prevent access outside the permitted folder tree.

Google Docs, Sheets, Slides and Drawings are exported as DOCX, XLSX, PPTX and
PDF respectively when downloaded through the workspace.

## Reviewer and HR guide

### Assign a professional activity

1. Open the HR dashboard at `/staff/hr/`.
2. Select **Assign activity**.
3. Search for and select one or more current staff members.
4. Choose the activity type: training, workshop, conference or event, meeting,
   or other.
5. Enter the title, organizer, location, description, start and end dates, and
   an optional report due date.
6. Submit the form.

The end date cannot be before the start date, and the report due date cannot be
before the activity ends. A separate assignment is created for each selected
staff member, and each person receives an email notification when email delivery
is configured.

An upcoming nomination can be removed while its start date is still in the
future and its status is **Nominated** or **Confirmed**. Removal changes the
assignment to **Cancelled** and notifies the staff member. Started, completed or
already-cancelled assignments cannot be removed through this action.

### Review an activity report

The HR dashboard lists submitted reports awaiting review and all activity
assignments. Open a report to inspect its text and download its supporting
documents, then choose one of the following actions:

- **Approve report** — marks the report approved and the assignment completed.
- **Request changes** — returns the report to the staff member for editing. A
  reviewer comment is required.

The staff member receives the decision and any comment by email. Reviewers can
download report documents, but only the report owner and authorized reviewers
can use the protected download endpoint.

### Review a profile submission

1. In Wagtail, open **Staff Profiles**.
2. Under **Awaiting review**, select **Review changes**.
3. Compare the current public values with the proposed values and portrait.
4. Choose **Approve and publish** or **Request changes**. A comment is required
   when requesting changes.

Approval publishes through the normal Wagtail revision mechanism. It is refused
if the Our Team page is locked, unpublished, has an unpublished draft, or the
staff profile changed after the submission was created. Resolve page-level
changes first. For a stale profile submission, request changes and ask the staff
member to submit a fresh update.

### Drive access for reviewers

Reviewers can browse the configured organization root and all app-managed staff
folders. Their upload, rename, move, download and trash operations are subject to
the same root-boundary validation and are recorded in the Drive audit log.

## Superuser guide

### Add and invite a staff member

1. Open **Staff Profiles → Add staff member**.
2. Select the published Our Team page.
3. Enter the full name, official title, department and optional profile details.
4. Keep **Send an invitation to manage this profile** selected and enter an
   unused work email, or clear it to create only the public profile.
5. Select **Add and publish staff member**.

The action publishes the staff record immediately and optionally sends a
password-setup invitation. If email delivery fails, the profile remains saved.
Correct the email settings and resend the invitation; do not create the staff
member again.

For a person who already has a platform account, create the profile without an
invitation and use **Link existing user**. Linking preserves the account's
password, groups, permissions and other platform access.

### Manage public team membership

The Our Team page contains an ordered **Staff shown on this page** selector.
Removing a selection hides the public card but does not delete the staff record,
account or history. An empty selection intentionally displays no staff.

Edit staff names, titles, departments, biographies, portraits and professional
links through **Staff Profiles → Edit details**. The registered account email is
managed separately under **Settings → Users**.

### Send invitations and profile reminders

The **Bulk profile invitations** panel includes eligible current staff who have
not completed a profile submission. Depending on account state, the message is
either a password-setup invitation or a reminder to update the profile.

Select the intended recipients, confirm the bulk action and send. The **Profile
email activity** table records the initiator, recipient, event, delivery status
and timestamp. In local console-email mode, messages appear in the application
terminal rather than an inbox.

### Offboard or reactivate staff

Use **Offboard / history** to mark a person **Retired** or **Left** with an
effective date of today or earlier. Offboarding immediately:

- removes the person from the public team output;
- blocks staff workspace access and password recovery;
- invalidates pending invitations;
- withdraws open profile submissions while retaining review history; and
- retains the staff record, portrait, reports and audit history.

The optional **Also disable the entire linked platform account** setting blocks
all account access, including CMS access. It is deliberately off by default.

Use **Reactivate / history** to restore current-staff status. Reactivation does
not re-enable a disabled platform account, resend an invitation, or reopen a
withdrawn submission. Handle those separately when appropriate.

## Workflow states

### Profile updates

```text
Draft → Awaiting review → Approved
                       ↘ Changes requested → new Draft
Draft/Awaiting review → Withdrawn on offboarding
```

Only one draft or submitted profile update can be open for an account at a time.
Approval changes the public profile; drafts and change requests do not.

### Activity reports

```text
Draft → Awaiting review → Approved
                       ↘ Changes requested → Awaiting review
```

An approved report completes its activity assignment. A cancelled assignment
cannot accept a report.

## Email notifications

With a working email backend and Celery worker, the system sends notifications
for:

- a new activity assignment;
- removal of an activity nomination;
- a submitted report awaiting HR review;
- report approval;
- requested report changes;
- a report due in two days; and
- an overdue report, once per day until it is submitted or approved.

Deliveries are de-duplicated and audited. Failed or pending messages are retried
by the periodic recovery task. Recipients come from linked account emails;
report-submission alerts go to active accounts explicitly assigned the
`staff.review_staff_profiles` permission.

## Deployment and configuration

### Required application services

The complete workflow expects:

- the ClimWeb web service;
- the database;
- an email backend for invitations and workflow messages;
- a Celery worker for email delivery and report attachment synchronization; and
- Celery beat for deadline reminders and recovery tasks.

Google Drive is optional. When it is disabled, profile, activity and report
workflows remain available, and report documents remain in protected local
storage.

### Database and static files

After deployment, run the normal migration and static collection commands:

```sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Local Docker equivalents are:

```sh
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py migrate --noinput
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py collectstatic --noinput
```

### Email

Configure the deployment's SMTP variables shown in `.env.sample`. Confirm that
`WAGTAILADMIN_BASE_URL` or the default Wagtail Site root URL is the public HTTPS
address; notification links are built from that value.

Do not invite real staff while using Django's console email backend. In that
mode, messages and invitation links are printed to the application logs.

### Private report storage

Report documents are stored below `PRIVATE_STAFF_REPORTS_ROOT`, which defaults to
`private_staff_reports` inside the application base directory. Production web
and worker services must share this private storage so authenticated downloads
and Drive synchronization can read the same files.

Include the database and private report storage in backups. They contain profile
review history, private draft portraits, activity reports, delivery records and
audit information that are not fully represented by public Wagtail media.

### Google Drive

Set the following values to enable Drive:

```env
GOOGLE_DRIVE_ENABLED=True
GOOGLE_DRIVE_SERVICE_ACCOUNT_HOST_FILE=./secrets/acmad-drive-service-account.json
GOOGLE_DRIVE_SHARED_DRIVE_ID=<shared-drive-id>
GOOGLE_DRIVE_ROOT_FOLDER_ID=<folder-id-inside-that-shared-drive>
```

Mount the service-account JSON read-only at the configured container path and
grant its `client_email` **Content manager** membership on the Shared Drive.
Then recreate the affected services and verify the connection:

```sh
docker compose --profile dev up -d --force-recreate climweb_dev
docker compose --profile dev exec -T climweb_dev \
  python /climweb/web/src/climweb/manage.py check_staff_drive
```

See [Staff portal Google Drive integration](staff-google-drive.md) for the full
setup and access model.

## Scheduled jobs

The application registers these periodic tasks:

| Task | Schedule | Purpose |
| --- | --- | --- |
| Staff report deadline reminders | Daily at 07:00 | Queue due and overdue report emails |
| Notification recovery | Hourly at minute 15 | Retry eligible pending or failed messages |
| Drive synchronization recovery | Every 15 minutes | Retry eligible pending or failed report uploads |

The schedule follows the Celery deployment's configured timezone.

## Security and audit notes

- Workspace ownership is resolved from the authenticated account, never from a
  staff identifier submitted by the browser.
- Former staff are denied workspace access even when they still have an active
  platform session.
- Public profile drafts and portraits remain private until approval.
- Report files use authenticated downloads and `nosniff` response headers.
- Drive operations validate the configured root and record mutating actions and
  downloads in `StaffDriveAudit`.
- Invitation tokens are stored as SHA-256 digests, expire after 48 hours and are
  invalidated when resent.
- Profile-only users are blocked from CMS, Django admin, API and general account
  management URLs by middleware.

## Troubleshooting

### An invitation or notification did not arrive

- Check whether the deployment is using the console email backend.
- Verify the SMTP settings and application logs.
- Check **Staff Profiles → Profile email activity** for profile invitation and
  reminder results.
- Check `StaffNotificationDelivery` in Django admin for activity workflow
  delivery status, attempts and the last error.
- After correcting email, resend a profile invitation or allow the notification
  recovery task to retry an eligible workflow message.

### A reviewer cannot open the HR dashboard

Confirm that the account is active, has `staff.review_staff_profiles`, is linked
to a current staff profile, and has accepted its invitation or otherwise has a
valid sign-in method.

### A profile cannot be approved

Check that the Our Team page is published, unlocked and has no pending draft.
Also check whether an administrator changed the staff profile after submission.
Resolve the page state or request a fresh staff submission rather than
overwriting newer content.

### A report is locked

Reports are intentionally read-only while **Awaiting review** and after
**Approved**. HR must request changes before the staff member can edit and
resubmit an awaiting report.

### Drive is unavailable

Run `python manage.py check_staff_drive` in the application environment. Verify
the four Drive settings, the mounted credential file, Shared Drive membership
and the configured root folder. Sharing only the root folder is insufficient;
the service account must be a Shared Drive member.

### A report attachment did not synchronize to Drive

The protected local copy should still be available. Check the document's Drive
sync status and error, ensure the worker can access the shared private-report
storage, and verify that Celery and Drive are configured. Failed uploads are
eligible for the 15-minute recovery task.

## Related documentation

- [Staff profile invitations and self-service](staff-profile-portal.md)
- [Staff portal Google Drive integration](staff-google-drive.md)
