# Access Transfer and Handover Acceptance

Do not store secret values in this document. Use the institution's approved password manager or direct transfer process.

## Access transfer register

| System | Current institutional owner | Successor | Access level required | MFA/recovery transferred | Verified date | Status/notes |
| --- | --- | --- | --- | --- | --- | --- |
| GitHub organization and repository |  |  | Admin/maintain as approved |  |  |  |
| GitHub Actions environments and secrets |  |  | Environment/repository admin |  |  |  |
| Production SSH/hosting account |  |  | Named least-privilege operator |  |  |  |
| Domain registrar |  |  | Domain administrator |  |  |  |
| DNS provider |  |  | DNS administrator |  |  |  |
| TLS/certbot host access |  |  | Server operator |  |  |  |
| Wagtail superuser and administrator groups |  |  | Role-specific |  |  |  |
| PostgreSQL backup storage |  |  | Backup/recovery operator |  |  |  |
| Media/private-file backup storage |  |  | Backup/recovery operator |  |  |  |
| SMTP/Mailgun sending domain |  |  | Email administrator |  |  |  |
| Google Workspace service accounts |  |  | Security/Workspace administrator |  |  |  |
| Google Shared Drive |  |  | Manager/content manager as approved |  |  |  |
| Google Calendar/Meet resources |  |  | Workspace administrator |  |  |  |
| Product source servers/THREDDS/SGBD |  |  | Read/operator as required |  |  |  |
| Monitoring/logging/OTel destination |  |  | Operator/administrator |  |  |  |
| Analytics/search verification |  |  | Institutional owner/editor |  |  |  |

For each system, verify sign-in, MFA, recovery contacts, billing/renewal owner, audit visibility, and removal or reduction
of former access. Rotate shared or exposed credentials after transfer.

## Technical acceptance checklist

- [ ] Contractual start date and handover scope approved.
- [ ] Canonical branches and final release SHA approved.
- [ ] Every feature branch classified and assigned a disposition.
- [ ] CI passes on the exact release SHA.
- [ ] Database migrations reviewed and applied successfully.
- [ ] Main site, RCC, Summer School, and CLIMSA routing validated as applicable.
- [ ] Product importer sources, schedules, workers, stop/retry, and public output validated.
- [ ] Email subscription and transactional notification tests completed.
- [ ] Staff invitation, profile, assignment, report, HR review, offboarding, and protected download tested.
- [ ] Google Drive and Meet integrations tested with institutional accounts, if enabled.
- [ ] Logs, monitoring, alerts, and escalation tested.
- [ ] Pre-release backup verified.
- [ ] Isolated database, media, and protected-file restore rehearsal completed.
- [ ] Rollback or forward-fix rehearsal completed.
- [ ] Architecture, deployment, environment-name, and storage inventories approved.
- [ ] Known issues and maintenance backlog have owners and target dates.

## Editorial and programme acceptance checklist

- [ ] Homepage carousel and featured content can be maintained by assigned editors.
- [ ] Products, publications, services, GIS links, and timeline documents are validated.
- [ ] RCC navigation, resources, products, and operational content are accepted.
- [ ] ENSO bulletin, explanation, news/events, and homepage presentation are accepted.
- [ ] Summer School editions, daily activities, reviews, media, and joining actions are accepted.
- [ ] CLIMSA navigation, branding, About content, outputs, products, publications, news, and events are accepted.
- [ ] Organization, leadership, staff, and Board content is accepted.
- [ ] Content migration counts, missing items, redirects, and rejected items are signed off.
- [ ] Mobile, browser, accessibility, localization, and broken-link checks are complete.

## Knowledge-transfer record

| Session | Audience | Trainer | Date | Practical exercise | Result | Follow-up owner/date |
| --- | --- | --- | --- | --- | --- | --- |
| Deployment and recovery | Infrastructure team |  |  | Deploy and isolated restore |  |  |
| Product/RCC operations | Product operators |  |  | Preview, run, stop/retry import |  |  |
| CMS editorial workflows | Editors |  |  | Create, preview, publish, revert |  |  |
| Staff workspace | HR/reviewers |  |  | Assignment through approval |  |  |
| Programme sites | RCC/CLIMSA/Summer School owners |  |  | Update programme content |  |  |
| Security and account ownership | System owners |  |  | Access/MFA/recovery verification |  |  |

## Outstanding-action register

| ID | Action | Priority | Owner | Dependency | Target date | Acceptance evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H-001 | Select canonical CLIMSA and Summer School branches | Critical |  | Branch review |  | Approved branch decision | Open |
| H-002 | Verify production SHA and service health | Critical |  | Production access |  | Signed environment evidence | Open |
| H-003 | Execute isolated restoration rehearsal | Critical |  | Verified backups |  | Restore record and smoke tests | Open |
| H-004 | Consolidate staff workspace and Drive documentation | High |  | Branch disposition |  | Merged canonical guides | Open |
| H-005 | Complete content migration ledger | High |  | Programme/editor review |  | Signed reconciliation | Open |
| H-006 | Transfer institutional external-service ownership | Critical |  | Current owners |  | Verified successor access | Open |
| H-007 | Transfer the handover documentation delta onto the recorded integration baseline | Critical | Documentation maintainer | Recorded `origin/develop` | 27 Oct 2026 | One-commit documentation-only diff | Complete; refresh refs before merge |

## Sign-off

Signing confirms that exceptions and open actions are explicitly recorded; it does not silently waive them.

| Role | Name | Decision | Conditions/exceptions | Signature/date |
| --- | --- | --- | --- | --- |
| Technical handover lead |  |  |  |  |
| Receiving technical lead |  |  |  |  |
| Editorial/operations lead |  |  |  |  |
| Information security/account owner |  |  |  |  |
| Project coordinator |  |  |  |  |
| Project executive |  |  |  |  |
