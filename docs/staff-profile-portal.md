# Staff profile invitations and self-service

## What is available

Staff can set their own password from an invitation, sign in to a restricted
profile portal, save a draft, and submit their biography, portrait, professional
website, LinkedIn, GitHub and publications URL for review. The existing public Our Team cards and
biography modals display approved content. Name, official job title, department,
ordering and membership of the public team remain administrator-managed.
Email icons use the linked user's registered email address, not an editable
profile field.

The portal is separate from the Wagtail CMS. Invitation-created accounts have
only My Profile, Change password and Sign out navigation. Linking an existing
platform account preserves its existing access without granting new CMS permissions;
linked users who already have CMS access also see a CMS dashboard link.

## Create and invite a new staff member

1. Sign in as a superuser and open **Staff Profiles → Add staff member**
   (`/cms-admin/staff-profiles/add/`).
2. Select the published Our Team page. If there is only one, it is preselected.
3. Enter the full name, official job title and department. Optionally add a
   biography, portrait, professional website, LinkedIn, GitHub and publications URL.
4. Leave **Send an invitation to manage this profile** checked and enter an
   unused work email, or uncheck it to create only the public profile.
5. Click **Add and publish staff member**. The profile appears immediately on
   Our Team; the optional invitation lets the person set their own password.

This action is superuser-only. It preserves existing profiles and refuses to
publish a locked page or one with pending unpublished changes. Resolve those in
Pages first. A matching name, title and department is rejected as a duplicate.
The page must already be published and departments must already be configured.

If email delivery fails, the public profile is still saved. Fix SMTP settings and
use the invitation form on Staff Profiles to resend to the newly selected member;
do not create the person again. Use **Staff Profiles → Edit details** for existing staff.

## Select staff on Our Team; edit details on Staff Profiles

- In **Pages → Organisation → Our Team**, the **Staff shown on this page** section
  contains only a staff selector and ordering controls. Select existing records,
  arrange them and publish. Names, photos, biographies and contact fields are not
  editable through this page's staff form. Page headings and introduction remain
  editable as page content.
- Removing a selection hides that card without deleting its staff record,
  account or review history, and without disabling its portal access. An empty
  selection deliberately shows no staff; it does not fall back to all members.
- Superusers manage names, roles, departments, photos and professional links via
  **Staff Profiles → Edit details**. Saving publishes the profile details while
  retaining the page selection. Locked pages, pending page drafts and stale
  profile edits are blocked to protect other editorial work.
- Staff continue to submit biography/photo/link updates for review. Email is
  displayed read-only in their portal, and is never changed through a submission.
- The email icon always uses the linked account's registered email. Without a
  linked account there is no email icon. Manage account emails under **Settings →
  Users**, checking the email-based username/login separately where necessary.
  Use **Link existing user** for an already registered account, as described below.

## Link an existing platform user

1. As a superuser, open **Staff Profiles** and find the staff member.
2. Click **Link existing user**. It appears for current staff who have no linked
   account yet. If you are creating the staff record first, leave **Send an
   invitation** unchecked, save, then use this action.
3. Select the existing account. Check its displayed name, registered email and
   username against the actual person.
4. Confirm that the account belongs to this staff member and that its email will
   appear publicly. Click **Link existing user**.

No password is changed, no invitation email is sent, and no groups, permissions,
staff/superuser flags or existing platform access are changed. The dashboard
records the linking administrator and timestamp. One account can belong to only
one staff profile, and existing links cannot be replaced through this action.
Disabled accounts, missing/invalid emails and duplicate registered email addresses
must be resolved in Settings → Users before linking. Former staff must first be
reactivated.

Existing users can continue their normal platform sign-in and visit `/staff/profile/`.
CMS users get a **My Staff Profile** menu item. Local-password users can also use
their registered email and existing password at `/staff/login/`, even when their
platform username is not an email address. External/SSO accounts retain their
existing sign-in method; linking does not create a local password.

Offboarding a linked existing user blocks the staff portal but retains their
other platform access unless **Also disable the entire linked platform account**
is explicitly selected. Invitation-created profile-only accounts retain their
original restrictions, even if someone later grants them CMS permissions.

The **Staff members** table includes saved staff records, even without a
portal account. Such records show **Not invited**, with an **Invite** link for
superusers that selects that person in the invitation form. Linked accounts show
Invitation pending, Active or Disabled. Portal status does not indicate whether
the public team page is published. Members only present in an unpublished page
revision are not yet saved live staff records.

## Offboarding retired or departed staff

1. As a superuser, open **Staff Profiles**.
2. Choose **Offboard / history** beside the person.
3. Select **Retired** or **Left** and enter the effective date (today or earlier).
4. Optionally check **Also disable the entire linked platform account**. This is
   unchecked by default and affects all account access, not just the staff portal.
   Verify the linked email before selecting it; you cannot disable your own account
   through this action.
5. Tick the confirmation and click **Confirm offboarding**.

Offboarding is immediate, even for a past effective date. Future scheduling is
not supported. Existing staff remain current until explicitly offboarded.

The person stays in the shared staff list with a **Retired** or **Left** status.
There are no Current/Former filters. Their public team card and any inherited
homepage DG identity disappear, but their profile, portrait and review history
remain stored. Separately written homepage DG messages/names must be reviewed in
the homepage editor; those text fields are not rewritten automatically. This is
not permanent data erasure: retained media files and old page revisions remain.

The portal denies login, profile updates and private photo access to former staff,
including already signed-in users. Staff password reset requests are suppressed;
old reset confirmation links are rejected while the profile is offboarded.
Pending invitation tokens are cancelled and draft/submitted profile updates are
marked **Withdrawn on offboarding**, retaining their content and review history.
Reviewers can still inspect the retained submissions but cannot approve them.

Employment status and its audit trail live outside Wagtail page revisions.
Offboarding does not publish or overwrite a pending Our Team draft, and restoring
an old revision cannot reactivate a former staff member. Public caches are cleared
after the change commits. Records with employment history are protected against
deletion through the page's inline editor; use offboarding rather than deleting.

### Reactivation

Open **Staff Profiles → Reactivate / history** beside the person, confirm, and click **Reactivate
staff member**. Their existing team profile is restored (subject to the team
page being published and the staff member being selected). The employment history records both transitions, their
effective dates, the administrator, timestamps and whether account disabling was
requested.

Reactivation does not re-enable a disabled platform account. If appropriate,
enable it separately under **Settings → Users** after checking its permissions.
Cancelled invitations must be resent; withdrawn submissions are not reopened.
An already activated, enabled account can use its existing password again.

## Pilot: invite an existing staff member

1. Sign in to the CMS with a superuser account.
2. Ensure the person already exists under **Staff Profiles**.
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
- Existing accounts are not automatically linked by the invitation form. Use
  the explicit, superuser-only **Link existing user** action to preserve their
  access. Transferring an already linked profile to another account is not supported.
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
Use **Link existing user** if a reviewer also needs a personal staff profile;
do not turn an invitation-created profile-only account into a CMS reviewer.

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

- Professional links are available in **Staff Profiles → Edit details**, the
  **Add staff member** form, and the staff self-service profile. Staff edits need
  approval, including changing or clearing these fields; the review screen shows
  current and proposed values.
- Website, LinkedIn, GitHub, publications and email icons appear on both the
  public staff card and its detail modal, only when their fields are populated.
  Publications is one URL (for example Google Scholar, ORCID or an institutional
  publications page), not a file upload or individual-publication list.
- The email icon publishes the staff member's **registered account email**.
  Use a work address suitable for public display when registering/inviting staff.
  Legacy public-email values remain in the database for history but are ignored
  by forms, approvals and public display. The email icon opens the
  visitor's configured mail application with a `mailto:` link; the website does
  not send an email automatically.
- Card contact links are separate keyboard-focusable controls, not nested inside
  the modal trigger. External links open in a new tab with `noopener noreferrer`.

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

Migration `staff.0004_staff_employment` adds employment status/history tables and
the withdrawn submission status. Apply it before serving the updated application.
It does not offboard anyone or change existing account access.

Migration `staff.0005_staff_contact_links` adds optional GitHub, publications and
legacy public email fields to public profiles and proposed updates.

Migration `staff.0006_staff_page_selections` copies existing saved staff membership
and ordering into selection records and upgrades page revision selections while
retaining the original profile data. It does not create or delete accounts. Review
any legacy draft-only staff entries that did not yet have a saved staff ID before
publishing an old draft; new staff must now be created under Staff Profiles.
Run migrations and collect static files before serving this update. Clear public
page caches once on deployment so older cached email links are refreshed:

```sh
python manage.py shell -c 'from wagtailcache.cache import clear_cache; from django.core.cache import cache; clear_cache(); cache.clear()'
```

Subsequent linked-account email changes invalidate public caches automatically.

Migration `staff.0007_staff_existing_accounts` adds the access mode and linking
audit fields. Existing invitation-created accounts remain profile-only by default.
The migration does not automatically link anyone or change user permissions.

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
They also cover staff creation with or without invitations, duplicate and email
validation, protected page drafts, creation permissions and SMTP failure recovery.
Offboarding tests cover public visibility across old revisions, current/former
lists, existing-session denial, invitation cancellation, review withdrawal,
explicit account disabling, reactivation, date/confirmation validation and cache
invalidation after commit.
Test emails use Django's in-memory email backend, not real staff inboxes.

## Later phases

- Email alerts for new submissions and review decisions; periodic update reminders.
- Administrator-verified account transfers and a dedicated email-change workflow.
- Submission retention/cleanup and a richer text editor if required.
- Optional dedicated portal theme settings and MFA for profile-only accounts.
