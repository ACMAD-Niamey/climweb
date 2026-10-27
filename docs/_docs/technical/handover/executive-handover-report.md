# ACMAD ClimWeb Executive Handover Report

## Document purpose

This report gives ACMAD leadership and the receiving operational team a concise account of what the ClimWeb project
has delivered, what has reached the recorded production branch, and what must still be verified before final
acceptance. It summarizes repository evidence available on 27 October 2026. It does not treat source code, commit
volume, or a branch name as proof that a service is running correctly in production.

The inherited ClimWeb repository begins on 3 February 2023. The ACMAD-specific implementation baseline used here is
6 August 2026, when scheduled ACMAD product imports first appear in the repository. That baseline remains subject to
confirmation against the contract and project initiation records.

## Executive conclusion

The project has moved ClimWeb from a general institutional content platform toward an integrated ACMAD service
environment. The repository now contains automated climate-product publication, Regional Climate Centre services,
programme sites, public subscription workflows, staff and HR workflows, institutional content, event services, and
the supporting deployment and operations material.

The implementation is substantial, and the recorded production branch includes the integration branch as of
23 October 2026. Final handover should nevertheless remain conditional. ACMAD still needs evidence from the running
environment, a complete branch disposition, a successful release-candidate test run, a restore rehearsal, a signed
content migration ledger, and verified transfer of institutional accounts and credentials.

The recommended executive decision is to accept the project into a controlled handover and stabilization phase. Final
unconditional acceptance should follow only when the critical actions in this report are closed and signed.

## Delivery evidence at a glance

| Evidence | Result on 27 October 2026 | Meaning |
| --- | ---: | --- |
| Earliest repository history | 3 February 2023 | Start of the inherited ClimWeb code history |
| ACMAD implementation baseline | 6 August 2026 | Reporting start for ACMAD-specific delivery |
| Unique commits across all available refs since baseline | 548 | Development activity, including work not yet integrated |
| Pull-request merge commits since baseline | 167 | Recorded integration activity, not a quality measure |
| Recorded integration head | `464bb584` dated 22 October 2026 | `origin/develop` after Summer School and CLIMSA integration work |
| Recorded production head | `714ee2ef` dated 23 October 2026 | Production ref containing the recorded integration head |
| Production relationship | 15 commits ahead of integration | Release history after the recorded integration head |
| Documentation candidate | `8432576d` dated 27 October 2026 | One documentation-only commit ahead of the recorded integration head |
| Initial documentation pack | 25 files and 2,409 added lines | Guides, registers, runbook, evidence, and acceptance material before this report |

These figures establish scale and traceability. They do not replace a test result, deployment record, content
reconciliation, or owner sign-off.

## What the project achieved

### Automated climate product operations

The project established a configurable product-import framework for historical and scheduled publication. Operators
can configure sources, run imports, monitor progress, stop or retry work, and inspect failures. Product families cover
dekadal and monthly bulletins, policy briefs, atmospheric analysis, heat stress, ITD and ITCZ monitoring, nowcasting,
climate and health, seasonal forecasts, climate watch, rainfall products, cryosphere products, and related RCC
outputs. Public subscription and notification workflows were added so approved product updates can reach registered
users.

This is a major operational shift from manual file placement toward managed ingestion with provenance and visible
operator controls. Production schedules, source availability, notification delivery, and per-family acceptance still
need to be checked in the running environment.

### Regional Climate Centre digital services

The RCC work created a dedicated landing experience, navigation, a data-services catalogue, climate-product pages,
ARC2 and CPC import workflows, station and country browsing, seasonal maps, climate indices, reference climatologies,
Climate Watch material, training and coordination pages, long-range forecasting forums, and subdomain support.

The implementation includes operator-facing import logs and stop controls. The remaining executive concern is not the
presence of the code, but whether each source, schedule, public route, and operational owner has been accepted and
recorded.

### Programme and thematic sites

The platform now supports distinct ACMAD programmes within one Django and Wagtail deployment. ENSO content includes
an Africa-focused page, bulletin presentation, explanatory content, related news and events, partner activities, and
homepage integration. Summer School work includes dedicated pages, edition promotion, application controls, online
joining actions, daily activities, reviews, galleries, and media. CLIMSA work includes a programme homepage,
navigation, About content, outputs, product and publication selections, news and events, subdomain configuration, and
programme-specific presentation.

This shared-platform approach reduces duplicated infrastructure while preserving separate editorial identities.
Programme owners must still approve final content, navigation, domains, redirects, and archive behavior.

### Public website and institutional content

The public site gained a configurable homepage carousel, featured products and events, services and partner sections,
an African RCC map, meteorological service directories, improved organization and service pages, a Director General
profile, Board of Governors content, an institutional timeline with supporting documents, GIS application links,
media galleries, video and quotation blocks, and multilingual publication metadata.

Editors can control more presentation choices without a code release. That flexibility requires a final role review,
content governance, accessibility checks, and practical editor acceptance.

### Staff and HR workspace

The staff implementation introduced invitation-only profiles, secure account setup, links to existing platform
accounts, self-service profile updates, review and publication, bulk invitations and reminders, offboarding, protected
portraits, activity assignments, multi-document reports, HR review, workflow notifications, and controlled file
downloads. Google Shared Drive integration supports staff folders and report synchronization when enabled.

This work carries the highest privacy and continuity obligations in the handover. ACMAD must confirm role boundaries,
institutional Google ownership, protected storage and backup, retention rules, account recovery, and offboarding
behavior before the workspace is considered fully accepted.

### Events forms and collaboration services

The project added ACMAD event migration tooling, media and document handling, safer HTML repair, updated event pages,
registration controls, closing-date enforcement, and Google Meet and Calendar integration. General forms gained
stronger deadline behavior and background export support.

The receiving team should run one controlled end-to-end event exercise covering publication, registration, email,
meeting creation, closing, export, retention, and revocation.

### Deployment security and continuity foundations

The repository defines Docker development and production profiles, PostgreSQL with PostGIS, Redis, Celery workers and
scheduling, nginx routing, multi-site subdomains, TLS procedures, CI testing, production deployment, backup and
restore commands, private storage, monitoring guidance, and access-transfer controls. Public authentication exposure
was reduced, and documentation now distinguishes public media from protected staff material.

The project has therefore created a credible operational foundation. The handover must prove that the documented
design matches the host, that backups cover every persistent store, and that a successor can restore the service
without relying on the original implementer.

## Delivery progression

| Period | Main delivery focus | Representative outcomes |
| --- | --- | --- |
| 6 to 31 August 2026 | Product automation and public platform foundations | ACMAD importers, importer monitoring and scheduling, product subscriptions, homepage redesign, RCC landing page, staff profile workflows, form controls, and institutional content improvements |
| September 2026 | RCC operations and service expansion | RCC datasets and importers, climate indices, climatologies, training and coordination, subdomain and TLS work, event migration, Google Meet, Board pages, OJT, participant mapping, and Africa-focused ENSO work |
| 1 to 27 October 2026 | Programme consolidation and internal operations | ENSO refinement, CLIMSA site, Summer School enhancements, configurable editorial controls, staff and HR workspace, Google Drive integration, leadership content, media improvements, and comprehensive operations and handover documentation |

## Current release and branch position

The recorded `origin/production` head is `714ee2ef` from 23 October 2026 and contains the recorded
`origin/develop` head `464bb584` from 22 October 2026. This improves the position reported in the earlier repository
snapshot, where production lagged development.

Most principal feature branches are now contained in both recorded heads, including product migrations, RCC, staff
profiles, staff-dashboard enhancements, CLIMSA, ENSO, Summer School integration history, Board content, subscriptions,
and homepage work. The following local lines still require a formal decision because their tips are not contained in
either recorded head:

- `summer-school-enhancement`, which has later news and media changes after the merged Summer School point;
- `ui-fixes`, which includes post-merge staff documentation and interface work;
- `goole-meet-integration`, which may be superseded but needs an explicit decision;
- `ojt`, which contains an event HTML repair command requiring confirmation of delivery or supersession;
- two backup branches that should be retained or archived under an approved evidence policy;
- the documentation candidate, which is intentionally awaiting review and merge.

No branch should be deleted until its unique commits, migrations, configuration changes, test result, and approved
disposition have been recorded.

## Readiness assessment

| Area | Executive assessment | Required evidence for closure |
| --- | --- | --- |
| Functional breadth | Substantial implementation across all agreed service areas | Owner-led acceptance by capability |
| Repository integration | Main feature history largely consolidated | Final branch register and approved disposition |
| Production traceability | Production ref contains the recorded integration head | SHA from the running host and deployment record |
| Test assurance | CI structure and a large test inventory exist; the local full-suite attempt exposed existing application failures and was stopped | Passing CI on the exact release SHA plus documented exceptions |
| Documentation | Strong technical, operational, editorial, and handover coverage has been added | Review, merge, owner assignment, and successor exercises |
| Content migration | Tools and programme content exist | Signed counts, missing-item log, redirects, and reviewer approval |
| Backup and recovery | Procedures and storage concepts are documented | Recent backup identifiers and an isolated restore rehearsal |
| Security and privacy | Role, secret, private-file, and offboarding guidance exists | Access review, credential transfer, retention decision, and controlled tests |
| External services | Email, Google services, product sources, DNS, and TLS are integrated or documented | Institutional ownership and controlled end-to-end verification |

## Critical matters before final acceptance

### Verify the running production environment

Record the deployed SHA, active services, migration state, worker and scheduler health, public domains, TLS validity,
representative static and media assets, and protected-file behavior. Repository evidence alone cannot establish these
facts.

### Establish a passing release baseline

Run the documented CI and application test suite against the exact release candidate. The local handover validation
attempt discovered failures in existing event, homepage, media, staff, tender, vacancy, and service-page tests before
it was stopped. Because the documentation change does not alter application code, these failures should be triaged
against the integration baseline and resolved or formally accepted before release sign-off.

### Complete branch disposition

Review every uncontained branch, especially the later Summer School, news, staff, Google Meet, and event-repair work.
Choose merge, supersede, archive, or close, and name the approver and acceptance test.

### Prove recovery and private data protection

Perform an isolated restore of the database, public media, private exports, and protected staff reports. Record the
recovery duration, missing items, corrective actions, and achieved recovery objectives.

### Close content and account ownership

Complete a migration ledger for products, RCC resources, events, Summer School, CLIMSA, staff, publications, news,
services, and institutional pages. Transfer GitHub, hosting, DNS, TLS, email, Google Workspace, source-server,
monitoring, analytics, and backup access to named institutional owners with MFA and recovery verified.

## Handover package

The receiving team should approve the following as one controlled package:

1. This executive report and the detailed project handover report.
2. The architecture, deployment, monitoring, recovery, release, and access guides.
3. Product migration and importer documentation.
4. RCC, ENSO, CLIMSA, Summer School, institutional content, media, staff workspace, and Google Drive guides.
5. The release and branch register.
6. The content migration and acceptance ledger.
7. The environment, domain, service, storage, and external-integration inventories.
8. Test, deployment, backup, restore, training, and access-transfer evidence.
9. A known-issues and maintenance backlog with owners and dates.
10. A signed acceptance record listing every exception.

## First 90 days after handover

### First 30 days

- Confirm the production SHA, services, domains, TLS, migrations, workers, schedules, and backup jobs.
- Merge and publish the reviewed documentation pack.
- Complete branch disposition and protect the agreed release branches.
- Transfer institutional access and rotate shared or exposed credentials.
- Run critical smoke tests for public pages, importers, subscriptions, staff workflows, and protected files.

### Days 31 to 60

- Complete the migration ledger and programme-owner content acceptance.
- Resolve or formally disposition the release-candidate test failures.
- Conduct the isolated restore and rollback exercises.
- Run role-specific training for infrastructure, editors, product operators, HR reviewers, and account owners.
- Establish monitoring alerts, retention, support escalation, and a maintenance rota.

### Days 61 to 90

- Close high-priority defects and documentation corrections found during real operation.
- Review source reliability, importer schedules, email delivery, Google integrations, and storage growth.
- Audit permissions, inactive accounts, private files, backups, and recovery contacts.
- Approve the steady-state maintenance backlog, service levels, and quarterly review calendar.
- Sign final acceptance or record the remaining exceptions with owners and target dates.

## Executive acceptance conditions

Final acceptance should be signed when all of the following are true:

- the contractual baseline and delivered scope are approved;
- the production SHA and service state are verified;
- the exact release candidate has a passing or formally accepted test record;
- all branches have an approved disposition;
- content migration is reconciled and accepted;
- backups have been restored successfully in isolation;
- institutional access and recovery ownership are transferred;
- protected staff and personal data controls are approved;
- operational and editorial successors have completed practical exercises;
- open issues have owners, priorities, dates, and acceptance tests.

## Sign off

| Role | Name | Decision and conditions | Signature and date |
| --- | --- | --- | --- |
| Project executive |  |  |  |
| Project coordinator |  |  |  |
| Receiving technical lead |  |  |  |
| Editorial and operations lead |  |  |  |
| Information security and account owner |  |  |  |
| Reporting expert | Yusuf Habu YUSUF |  |  |
