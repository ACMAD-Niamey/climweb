# Manage the Staff Workspace

The staff workspace is a private area for staff profiles, professional activity assignments, reports, HR review, and
organization files. It is separate from the public Our Team page and from the Wagtail CMS.

## Entry points

| Area | Default path | Intended user |
| --- | --- | --- |
| Sign in | `/staff/login/` | Current staff with a linked active account |
| Dashboard | `/staff/` | Current staff |
| My Profile | `/staff/profile/` | Current staff |
| Activities and reports | Staff workspace navigation | Current staff |
| Organization files | `/staff/files/` | Current staff; scope depends on permission |
| HR dashboard | `/staff/hr/` | Linked current staff with review permission |
| Staff Profiles administration | `/cms-admin/staff-profiles/` | Authorized CMS reviewers/superusers |

Workspace pages require authentication and are marked `noindex, nofollow`.

## Roles and permissions

| Capability | Staff member | Reviewer/HR | Superuser |
| --- | :---: | :---: | :---: |
| Edit and submit own profile | Yes | Yes | Yes |
| View own assignments and reports | Yes | Yes | Yes |
| Browse own Drive folder | Yes | Yes | Yes |
| Browse all managed Drive folders | No | Yes | Yes |
| Assign activities and review reports | No | Yes | Yes |
| Review profile submissions | No | Yes | Yes |
| Add, link, offboard, or reactivate staff | No | No | Yes |
| Send invitations and bulk reminders | No | No | Yes |

Reviewer access uses `staff.review_staff_profiles` plus normal Wagtail admin access. Publishing profile updates also
requires Edit and Publish permission on the relevant Our Team page. HR users need a linked current staff profile because
the HR dashboard is inside the staff workspace.

Do not turn a restricted invitation-created account into a reviewer as a shortcut. Link the reviewer's existing platform
account and grant only the required group permissions.

## Staff workflow

### Activate and sign in

Invitation links are single-use and expire after 48 hours. Staff set a password, then sign in with their registered work
email. Existing linked accounts keep their existing authentication method.

### Update a profile

Staff can propose biography, portrait, website, LinkedIn, GitHub, and publications links. **Save draft** keeps the update
private; **Submit for review** locks it until approval or a request for changes. Name, official title, department, account
email, and team-page membership remain administrator-managed.

Portraits accept JPEG, PNG, or WebP, up to 5 MB and 4096 × 4096 pixels. They are re-encoded, stripped of metadata, and
reduced before publication.

### Complete an activity report

1. Open the assignment.
2. Enter title, summary, outcomes, and follow-up actions.
3. Attach up to three supported documents, each no larger than 10 MB.
4. Save a draft or submit to HR.

Report files use authenticated downloads and are not public media. An approved report completes the assignment. A
cancelled assignment cannot receive a report.

## HR/reviewer workflow

### Assign an activity

From `/staff/hr/`, select one or more current staff, activity type, title, organizer, location, description, start/end
dates, and optional report due date. The due date cannot precede the activity end. Each recipient receives a separate
assignment and, when configured, an email notification.

Upcoming nominations can be cancelled only while eligible. Cancellation is retained as state/history and not deleted.

### Review a report

- **Approve report:** marks the report approved and the assignment completed.
- **Request changes:** returns it for editing and requires a reviewer comment.

Download attachments only through the protected endpoint. Do not copy them into Wagtail public media.

### Review a profile

Compare current and proposed values in **Staff Profiles → Awaiting review**. Approval is blocked when the team page is
locked, unpublished, has an unpublished draft, or the underlying profile changed after submission. Resolve page-level
work first; request a fresh submission when a proposal is stale.

## Superuser lifecycle

- Add and optionally invite new staff through **Staff Profiles**.
- Use **Link existing user** for an existing account; linking preserves its password, groups, and permissions.
- Use bulk invitations/reminders only after verifying recipients and email configuration.
- Use **Offboard/history** for retired or departed staff instead of deleting records.
- Use **Reactivate/history** when appropriate; reactivation does not automatically enable a disabled platform account or
  reopen withdrawn submissions.

Offboarding removes public/team output and workspace access, invalidates invitations, and withdraws open submissions
while retaining profile, report, and audit history. Disabling the whole platform account is a separate explicit choice.

## Notifications and scheduled work

The complete workflow expects web, database, email, Celery worker, and Celery beat services. Notifications cover new or
cancelled assignments, submissions, approvals, change requests, upcoming deadlines, and overdue reports. Delivery is
audited and failed/pending records are retried by periodic recovery work.

Google Drive is optional; local protected report storage remains authoritative for workspace downloads.

## Deployment and verification

Use the deployed release's normal migration/static process, then verify:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check
```

Production web and worker services must share the private staff-report volume. Include that volume and the database in
backups.

Perform a controlled acceptance path:

1. Invite or link a test staff account.
2. Submit and approve a profile update.
3. Assign an activity.
4. Submit a report with a harmless test document.
5. Request changes, resubmit, and approve.
6. Verify protected download authorization and notification history.
7. Offboard the test profile and confirm immediate workspace denial.

## Security and retention

- Ownership comes from the authenticated account, never a browser-supplied staff ID.
- Former staff remain denied even with an existing session.
- Draft portraits and report documents remain private.
- Invitation tokens are stored as digests and invalidated when resent.
- Define retention for reports, drafts, portraits, notification records, Drive audits, and employment history.
- Restore tests must include protected files, database relationships, and authorization—not only public pages.

See [Staff profile invitations and self-service](../../staff-profile-portal.md) for detailed invitations, linking,
profile review, offboarding, and portrait behavior.
