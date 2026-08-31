# Staff profile invitations and self-service

## What is available

Staff can set their own password from an invitation, sign in to a restricted
profile portal, save a draft, and submit their biography, portrait, professional
website and LinkedIn URL for review. The existing public Our Team cards and
biography modals display approved content. Name, official job title, department,
ordering and membership of the public team remain administrator-managed.

The portal is intentionally separate from the Wagtail CMS. It has only My Profile,
Change password and Sign out navigation. It does not give staff permission to edit
the shared Our Team page or browse the rest of the CMS.

## Pilot: invite one staff member

1. Sign in to the CMS with a superuser account.
2. Ensure the person already exists under **Pages → Organisation → Our Team**.
   Save and publish any pending page changes before testing profile approval.
3. Open **Staff Profiles** in the CMS sidebar (normally
   `/cms-admin/staff-profiles/`).
4. Select the existing staff record and enter their individual work email.
5. Click **Send invitation**. This creates a profile-only account; its login is
   the email address. No default password is assigned.
6. The staff member opens the email link, sets a password and signs in at
   `/staff/login/`. They land on `/staff/profile/`.
7. Staff edit their details, optionally save a draft, then submit for review.
8. An administrator opens **Staff Profiles → Awaiting review → Review changes**,
   compares the current and proposed profile, and approves or requests changes.
9. After approval, open the public team card and confirm the biography, portrait
   and links. Requesting changes leaves the public profile untouched and shows the
   reviewer's comment in the staff member's activity history.

On localhost, use an email inbox you control for the pilot. A localhost invitation
only opens on the computer running this app; send real staff invitations from the
deployed HTTPS website. This feature does not send invitations automatically.

## Invitations, password recovery and access

- Invitation links are random, stored as SHA-256 digests, valid for 48 hours, and
  single-use. Resending a pending invitation immediately invalidates its old link.
- Resend by selecting the same staff member and email in the invitation form.
- If SMTP delivery fails, the passwordless account remains available for resend.
  Correct the email settings before trying again.
- Existing accounts are not automatically linked or downgraded. This prevents
  unintentionally repurposing an administrator account. Account transfer and email
  correction need a separate, verified administrator procedure in a later phase.
- Activated staff can use **Forgot your password?** or **Change password**.
  Password resets use Django's configured password-reset timeout. They are only
  emailed for active, password-enabled staff profile accounts.
- To disable access, use **Settings → Users** and make the account inactive.
  This also invalidates its invitation and prevents sign-in. Do not delete the
  user just to disable access: deletion removes linked profile-update history.
- Profile accounts receive neither superuser/staff flags nor CMS group permissions.
  The middleware also blocks their CMS, Django admin, API and general account
  management URLs. Visiting the CMS root redirects them to My Profile.
- Public website pages remain accessible. The profile portal resolves ownership
  from the authenticated account, never from an editable staff ID.

## Review permissions and publication

Superusers can invite staff and review submissions. To delegate reviews, assign
`staff.review_staff_profiles` ("Can review staff profile submissions") and the
normal Wagtail admin-access permission to a trusted communications reviewer.
Their Wagtail group must also have Edit and Publish page permissions on the
specific Our Team page; approval respects Wagtail's existing publish permission.
Reviewers do not gain invitation/account-creation rights from that permission.
Do not link a reviewer account to a profile-only staff account.

Only one draft or pending submission is allowed per account. Pending submissions
cannot be edited. A request for changes closes the previous submission; the next
draft is a new record, retaining the previous review and its comments.

Approval publishes through Wagtail's page revision mechanism and records the
reviewer and timestamp. It refuses to publish when the team page is locked,
unpublished, or has an unpublished draft, or when the staff record changed since
the draft was created. Resolve page-level drafts first; for a profile conflict,
request changes and have the staff member submit a fresh draft. These checks
avoid silently overwriting unrelated editorial work.

## Photos and text

- Biography input is plain text. Blank lines separate paragraphs; submitted HTML
  is escaped when published. Existing rich-text biographies remain unchanged
  until a proposed update is approved.
- Photos accept JPEG, PNG and WebP up to 5 MB and 4096 × 4096 pixels. The app
  re-encodes them as JPEG, strips metadata and limits the stored image to 1600 pixels.
- Draft portraits are stored as binary data with the private submission, not in
  the public media library. Preview responses require the owner or a reviewer and
  disable caching. On approval, a new Wagtail image is created.
- This small-team pilot retains submission history and private draft portraits.
  Include this database content in backups and set a retention policy before
  rolling it out at larger scale.

## Deployment

Run the normal application migration and static collection steps after deploying:

```sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Local development equivalents:

```sh
docker compose --profile dev exec -T climweb_dev python /climweb/web/src/climweb/manage.py migrate --noinput
docker compose --profile dev exec -T climweb_dev python /climweb/web/src/climweb/manage.py collectstatic --noinput
```

Migration `staff.0003_staffmember_linkedin_staffmember_website_and_more` adds the
professional links, account mapping and submission tables. It does not create
accounts, alter existing staff content or send email.

Invitations and password-reset messages use the existing Django email settings:
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS` / `EMAIL_USE_SSL`, and `DEFAULT_FROM_EMAIL`. Use a verified sender
and a functioning SMTP service. In local development, the default `EMAIL_BACKEND`
is `django.core.mail.backends.console.EmailBackend`: messages appear in the
application terminal instead of an inbox. The invitation dashboard displays a
warning in this mode. For real delivery, set
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` as well as the SMTP
settings and recreate the app container to load the environment changes.
Password reset requests are limited to five per email/client address per 15 minutes
using the configured shared cache; retain normal proxy-level rate limits as well.
Email URLs use the request's host and scheme;
ensure the reverse proxy correctly forwards HTTPS and the configured allowed host
is the public domain. Protect invitation/reset URL logs as sensitive and avoid
shared caching on `/staff/`.

The portal uses `Referrer-Policy: same-origin` (and an equivalent HTML meta tag).
Do not change it to `no-referrer`: browsers can send `Origin: null` on native form
POSTs under that policy, causing Django to reject password setup and other forms.
Do not trust the `null` origin or disable CSRF protection to work around this.
After a policy change, reopen the invitation URL or reload the form before posting.

## Verification

```sh
docker compose --profile dev exec -T climweb_dev python /climweb/web/src/climweb/manage.py test climweb.pages.organisation_pages.staff.tests --keepdb
```

Tests cover invitations, password validation, expiry, reuse and resend, ownership,
restricted endpoints, CSRF, drafts, review decisions, conflicting page edits,
private photo access, upload validation, publication and password recovery.
Test emails use Django's in-memory email backend, not real staff inboxes.

## Later phases

- Email alerts for new submissions and review decisions; periodic update reminders.
- Administrator-verified account linking, email changes and account transfers.
- Submission retention/cleanup and a richer text editor if required.
- Optional dedicated portal theme settings and MFA for profile-only accounts.
