# Comprehensive ACMAD ClimWeb Project Handover Report

## Document control

| Field | Value |
| --- | --- |
| Project | ACMAD website modernization, product migration, and digital services integration |
| Implementation baseline | 6 August 2026 (subject to contractual confirmation) |
| Audit date | 27 October 2026 |
| Prepared from | Git history across all locally available branches and repository documentation |
| Repository | `ACMAD-Niamey/climweb` |
| Technical handover status | Draft — requires environment, ownership, and acceptance validation |
| Reporting expert | Yusuf Habu YUSUF |

## Executive summary

The ACMAD implementation extends ClimWeb into a multi-site institutional platform supporting the main ACMAD website,
Regional Climate Centre services, programme sites, automated climate-product publication, editorial workflows, events,
staff operations, and external integrations.

Repository history from the ACMAD baseline to the audit date contains 538 unique commits across all refs and 159 merge
commits whose messages identify pull-request merges. These are development-volume indicators, not acceptance metrics.
The delivered value must be assessed by capability, deployment state, test evidence, documentation, and operational
ownership.

At the audit date:

- `origin/develop` points to `c79d0d06` (20 October 2026, PR #192).
- `origin/production` points to `eeb2f699` (15 October 2026, PR #183).
- Later work exists on feature branches and must not be described as production until it is integrated, deployed, and
  validated.
- The first `documentations` branch was created from commit `7e5f02ba` on the local `climsa-website` line. The initial
  evidence capture found it 4 commits ahead of and 161 commits behind `origin/develop`. On 27 October 2026, the
  documentation-only change was reapplied to recorded `origin/develop`; the corrected candidate was then exactly one
  commit ahead of that integration head.

## Evidence collected on 27 October 2026

The repository evidence snapshot confirms the following without requiring production access:

- 27 local branches were inspected: 16 were ancestors of both recorded remote heads, 2 were ancestors of
  `origin/develop` but not `origin/production`, and 9 were ancestors of neither.
- `codex/summer-school-gallery` and `staff-dashboard-enhancements` were integrated into `origin/develop` but not
  `origin/production` at the snapshot.
- The recorded `origin/develop` Compose configuration defines 13 services and 7 named volumes, including the
  production private staff-report volume.
- The recorded integration branch contains 50 executable management-command modules, 422 migration files, and 142
  test files by repository filename inventory.
- CI is configured for pushes and pull requests to `develop` and `production`; deployment is restricted to a push to
  `production` after the test job.
- The staff Google Drive guide exists on both recorded remote heads. The broader staff workspace guide exists on the
  local `ui-fixes` branch and is not yet on the recorded integration head.
- Repository whitespace/diff checks passed for the handover changes. Runtime tests were not executed because the local
  Docker daemon was unavailable; a documentation build was not executed because Sphinx was absent from the runtime.

These facts are repository evidence only. The production SHA, running services, enabled configuration, data state,
external accounts, backups, and public/protected workflow behavior remain pending authorized environment validation.

## Project objectives

1. Modernize ACMAD's public website and editorial experience.
2. Migrate and continuously publish ACMAD climate products from authoritative sources.
3. Build an Africa-focused RCC digital service with navigable datasets, resources, and operational import controls.
4. Support programme-specific experiences for ENSO, Summer School, CLIMSA, OJT, and related initiatives.
5. Improve staff profiles, assignments, reporting, review, notifications, and controlled file access.
6. Establish repeatable deployment, subdomain, TLS, backup, testing, and operational practices.

## Achievement register

The status in this table describes repository evidence. "Production included" means the relevant commit is reachable
from the recorded production ref; it does not replace a live-environment acceptance test.

| Workstream | Capability achieved | Principal evidence | Handover state |
| --- | --- | --- | --- |
| Product migration | Configurable ACMAD product importers, provenance, manual history import, schedules, progress, stop/retry, and source testing | `pages/products`; product importer and ACMAD migration guides | Substantial implementation and documentation; live schedules and source health require verification |
| Product coverage | Import families for rainfall, dekadal and monthly bulletins, policy briefs, atmospheric analysis, heat stress, ITD/ITCZ, nowcasting, climate-health, seasonal forecasts, climate watch, cryosphere, and related products | Management commands and importer registry | Validate every enabled family against production configuration |
| RCC | RCC pages, datasets, ARC2/CPC workflows, climate products, indices, resources, training, coordination, long-range forecasting, import controls, and subdomain support | `pages/services`; `rcc-website`; subdomain guide | Core work merged historically; current content, scheduled jobs, and public navigation require acceptance |
| ENSO | Africa-focused ENSO/El Niño page, bulletin presentation, explanation content, related news/events, partner activities, and homepage integration | `el-nino-africa`; `seed_el_nino_page` | Merged to development history; editorial guide and live content review outstanding |
| Homepage and editorial controls | Configurable carousel, featured products/events, programme slides, organization and service-page controls | `hero-carousel-mods`; `ui-fixes`; homepage guide | Core changes integrated; schema and final editorial settings require verification |
| Product subscriptions | Hardened public subscriptions, subscriber controls, notifications, privacy safeguards, and Mailgun/SMTP deployment guidance | `fix/subscription-form`; subscription guide | Code and guide available; sender domain, delivery, consent export, and suppression behavior require live test |
| Staff profiles | Invitations, linked accounts, self-service profile updates, review/publish workflow, bulk reminders, offboarding, and protected portraits | `acmad-staff`; staff profile guide | Implemented; current permissions, account ownership, and retention require confirmation |
| Staff workspace | Activity assignment, reports, multiple documents, HR review, email notifications, and protected downloads | `staff-dashboard-enhancements`; `ui-fixes` | Code largely merged; canonical documentation must be promoted with the release |
| Google Drive | Shared Drive browsing and controlled operations, personal folders, audit trail, and report-document synchronization | `staff-dashboard-enhancements`; branch-only Drive guide | Credentials, Shared Drive permissions, Celery sync, and recovery procedure require operational acceptance |
| Institutional content | Director General profile, staff presentation, Board of Governors, organization pages, timeline and multiple supporting documents | `ui-fixes`; `board-of-governors` | Validate final content, translations, permissions, and mobile presentation |
| Events and meetings | Event UI, registration content migration, Google Meet integration, and event HTML repair tooling | `UI-modifications`; `events-migrations`; `goole-meet-integration` | Several components merged; Google ownership and end-to-end email/meeting flow require verification |
| Summer School | Dedicated pages and subdomain, featured edition, joining actions, daily activities, reviews, gallery and media enhancements | `summer-school-enhancement`; related commits | Later work remains on a feature branch; integrate and test before production claim |
| CLIMSA | Programme homepage, navigation, About page, outputs, products, news/events/publications selectors, subdomain command, and deployment configuration | `climsa-website`; `codex/climsa-website-clean` | Feature-branch implementation; branch consolidation, content migration, DNS/TLS, and acceptance remain |
| News and media | Video and quotation blocks, gallery video support, multilingual publication metadata, and media presentation improvements | `summer-school-enhancement`; `ui-fixes` | Later branch work requires integration, migration, and regression testing |
| Deployment | Docker dev/prod profiles, CI tests, production deployment pipeline, nginx variants, multi-site routing, TLS guidance, Celery worker/beat | deployment, subdomain, and TLS guides | Documented; validate host reality, access, backups, deployed SHA, and rollback rehearsal |

## Architecture and operational boundaries

The implementation is a Django and Wagtail application using PostgreSQL/PostGIS, Redis, Celery worker and beat,
Docker Compose, and nginx. Wagtail Sites provide programme subdomains while the sites share an application and database.
Private staff reports and public media have different access requirements and must not be treated as interchangeable.

The production handover must include an approved diagram showing:

- public DNS and TLS termination;
- nginx to application routing;
- web, database, Redis, worker, beat, and seed services;
- persistent database, media, static, backup, private-export, and private-report storage;
- external product sources, SMTP/Mailgun, Google services, and monitoring destinations;
- trust boundaries for public, CMS, staff, HR, and server-administration access.

## Deployment and environment acceptance

Before sign-off, an authorized operator must record:

| Item | Required evidence | Result |
| --- | --- | --- |
| Deployed application commit | SHA reported from the production checkout and application | Pending |
| Active Compose services | Redacted service/status output | Pending |
| Public domains | HTTP status, TLS validity, correct Wagtail Site routing | Pending |
| Database migrations | `showmigrations` review and successful migration record | Pending |
| Celery worker and beat | Healthy services and one verified scheduled task | Pending |
| Static and media assets | Representative asset validation on every hostname | Pending |
| Product sources | Test/preview for each enabled importer family | Pending |
| Email | Successful controlled transactional email and unsubscribe test | Pending |
| Google integrations | Authorized test of configured Meet/Drive flows | Pending |
| Backup and restore | Recent backup identifiers plus isolated restoration evidence | Pending |

## Data and content migration

Create a signed migration ledger rather than relying on visual inspection. Each source collection must record source URL
or system, expected records, imported records, rejected records, missing files, redirect rules, transformation decisions,
duplicate handling, responsible reviewer, and acceptance date.

Collections requiring explicit closure include ACMAD products, RCC resources and archives, events and registrations,
Summer School editions and media, CLIMSA pages and documents, staff profiles, organization history, publications, news,
services, and programme-specific navigation.

## Security, privacy, and access

- Rotate or transfer all privileged credentials through an approved secret manager or direct owner-to-owner process.
- Verify least-privilege roles for GitHub, server SSH, Wagtail administrators, staff reviewers, Google Workspace,
  email services, DNS, and domain registration.
- Confirm that private activity reports and staff files are absent from public media URLs and backups have equivalent
  access controls.
- Record retention and deletion decisions for registrations, subscriber consent, staff history, activity reports,
  audit logs, and uploaded documents.
- Perform a final dependency, configuration, permission, and public-authentication review before acceptance.

## Testing and quality assurance

The final evidence pack should contain:

1. CI result for the exact release commit.
2. Migration test on a production-like database copy.
3. Smoke tests for every domain and major navigation route.
4. Editor tests for create, preview, publish, unpublish, permissions, and cache invalidation.
5. Importer tests for source validation, preview, manual execution, progress, stop, retry, and scheduled execution.
6. Staff/HR tests for invitation, sign-in, assignment, reporting, review, private download, offboarding, and audit records.
7. Mobile, accessibility, security, email, backup/restore, and rollback evidence.

## Known risks and outstanding decisions

| Risk or decision | Impact | Required closure |
| --- | --- | --- |
| Feature work exists outside `origin/develop` and `origin/production` | Achievements may be overstated or code may be lost | Classify and disposition every branch in the branch register |
| Production SHA and live configuration are not verified by Git history alone | Report may not match the running service | Authorized production inspection and signed evidence |
| CLIMSA and Summer School histories overlap | Merge conflicts or duplicate migrations | Select canonical branches and run migration/regression review |
| Staff documentation is split across branches | Operators may miss security-critical procedures | Merge reviewed staff workspace and Drive guides into the canonical release |
| Backup guide does not prove a recent isolated restoration | Recovery may fail when needed | Execute, time, and document a restoration rehearsal |
| External service ownership may remain with an individual | Service interruption after handover | Transfer to institutional accounts and verify successor access |
| Content migration counts are not consolidated | Missing or duplicate public content may go unnoticed | Complete and sign the migration ledger |
| Documentation was initially based on a divergent CLIMSA line | A direct merge could have included unrelated feature work | Resolved on 27 October: documentation-only delta reapplied to recorded `origin/develop`; verify again after refreshing remote refs |

## Training and knowledge transfer

Run recorded, role-specific sessions for:

- infrastructure and deployment operators;
- Wagtail administrators and editors;
- RCC/product-import operators;
- staff-workspace reviewers and HR personnel;
- account and security owners;
- project management and acceptance representatives.

Each session must include a practical exercise, attendance, materials, unresolved questions, and named follow-up owner.

## Final deliverables

- Approved comprehensive handover report.
- Release and branch register with final disposition.
- Architecture and deployment diagram.
- Redacted environment/configuration inventory.
- Migration ledger and content acceptance record.
- Test and deployment evidence pack.
- Backup and restoration evidence.
- Access-transfer register.
- Training record.
- Known-issues and maintenance backlog.
- Signed acceptance certificate.

## Approval

| Role | Name | Decision | Signature/date |
| --- | --- | --- | --- |
| Reporting expert |  |  |  |
| Technical recipient |  |  |  |
| Editorial/operations recipient |  |  |  |
| Project coordinator |  |  |  |
| Project executive |  |  |  |
