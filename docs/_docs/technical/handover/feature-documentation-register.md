# Feature Documentation Register

This register tracks whether a capability has enough material for development, administration, operations, security,
and recovery. A source-code implementation or a short feature note is not a complete handover.

## Guide implementation status

The following gap-closing guides were added on the documentation branch:

| Critical area | Canonical guide |
| --- | --- |
| ACMAD-specific service/storage/trust architecture | `technical/acmad-architecture.md` |
| Production monitoring and incident response | `technical/operations-monitoring.md` |
| Account ownership, secrets, rotation, and offboarding | `technical/access-and-secrets-management.md` |
| Complete recovery scope and restore rehearsals | `technical/disaster-recovery.md` |
| Branch integration, migrations, promotion, and closure | `technical/release-management.md` |
| Migration ledger, reconciliation, sampling, and acceptance | `technical/content-migration-acceptance.md` |
| RCC editorial and operational management | `manage_pages/Manage-RCC.md` |
| ENSO content, bulletins, imports, and homepage behavior | `manage_pages/Manage-ENSO.md` |
| CLIMSA content, navigation, migration, and release acceptance | `manage_pages/Manage-CLIMSA.md` |
| Summer School editions, applications, media, and privacy | `manage_pages/Manage-Summer-School.md` |
| Institutional leadership, Board, timeline, GIS, and CUIP content | `manage_pages/Manage-Institutional-Content.md` |
| News video, quotations, galleries, media rights, and accessibility | `manage_pages/Manage-News-and-Media.md` |
| Staff activities, reports, HR review, notifications, and protected files | `manage_settings/Manage-Staff-Workspace.md` |
| Staff Shared Drive setup, security, synchronization, rotation, and recovery | `manage_settings/Manage-Staff-Google-Drive.md` |

These guides close the documentation-structure gaps. Environment-specific owners, configuration values, test evidence,
screenshots, migration counts, and sign-offs still require validation by the responsible ACMAD teams.

## Coverage and gaps

| Capability | Existing material | Critical additions | Completion evidence |
| --- | --- | --- | --- |
| Deployment and CI/CD | Deployment guide and workflow | Confirm real host paths, owners, environment promotion, maintenance window, rollback rehearsal | Reviewed runbook plus successful witnessed deployment |
| DNS, subdomains, nginx, TLS | Subdomain and TLS guides | Domain registrar/DNS ownership, active config inventory, expiry alerts, CLIMSA final activation | Verified domain matrix and certificate check |
| Backup and restore | Basic backup/restore guide | Retention, off-host copy, encryption, private files, RPO/RTO, isolated restore results | Signed restore rehearsal |
| Product import platform | Importer feature and ACMAD migration guides | Enabled-production register, source SLAs, operator rota, alerting and per-source acceptance | All enabled importers previewed and one schedule observed |
| RCC | Technical implementation and commands | Editor guide, data-source ownership, importer schedule matrix, public acceptance checklist | RCC owner sign-off |
| ENSO | Source implementation and commits | Editor guide, content ownership, bulletin replacement/archive procedure, homepage rules | Editorial exercise and live review |
| Homepage/editorial controls | Homepage carousel guide | Complete role matrix, fallback behavior, cache behavior, release-independent editorial checks | Editor sign-off |
| Products/publications/services | General editor and importer guides | ACMAD taxonomy decisions, GIS links, multilingual metadata, timeline/CUIP guidance | Sample create/edit/publish exercise |
| Product subscriptions | Administrator/deployment guide | Institutional sender ownership, consent export/retention, incident and suppression workflow | Controlled subscribe/send/unsubscribe test |
| Staff profiles | Detailed portal guide | Canonical release location, institutional account policy, privacy/retention approval | HR and security sign-off |
| Staff workspace/reports | Guide currently on `ui-fixes` | Merge to canonical docs, operational ownership, protected-volume backup/restore | Staff and HR workflow test |
| Google Drive | Guide currently on a staff feature branch | Credential transfer, Shared Drive ownership, audit retention, outage/retry/recovery | `check_staff_drive` and controlled file exercise |
| Google Meet/events | Meet guide and event implementation | Institutional service-account ownership, calendar lifecycle, email failure and revoke procedure | Controlled registration/meeting/email test |
| Summer School | README/subdomain references and code | Full editor guide, edition lifecycle, daily activities, reviews, media/video, archive procedure | Programme-owner acceptance |
| CLIMSA | Migration audit, code, subdomain guide | Final content ledger, editor guide, partner branding, navigation, outputs/products/publications, redirects | Programme-owner acceptance |
| News/media | General CMS material and code | Video/quote/gallery blocks, supported providers, moderation, accessibility, media retention | Editor exercise on candidate release |
| Security and access | Distributed role/config notes | Consolidated access matrix, ownership, offboarding, secret rotation, incident escalation | Access review and transfer register |
| Monitoring and observability | Compose/OTel configuration | Production dashboards, alerts, log retention, health thresholds, escalation | Simulated alert and operator response |
| Architecture/data model | General architecture guide | ACMAD-specific diagram, page tree, app/data ownership and trust boundaries | Technical review approval |
| Content migration | CLIMSA audit and product migration notes | Unified record-count ledger, missing assets, redirects, rejected items and approval | Signed migration reconciliation |
| Accessibility and localization | General platform support | Audit of new ACMAD templates/media, alt text, keyboard behavior, language completeness | Recorded audit and remediation list |

## Minimum feature document

Every major feature should document:

1. Purpose and business owner.
2. User roles and permissions.
3. Entry points, normal workflow, and screenshots where useful.
4. Data model and storage classification.
5. Configuration names and external dependencies, without secret values.
6. Background jobs, schedules, retries, and failure handling.
7. Deployment and migration steps.
8. Monitoring, logs, health indicators, and support escalation.
9. Backup, restoration, retention, and deletion behavior.
10. Security and privacy considerations.
11. Tests and acceptance procedure.
12. Known limitations and maintenance owner.

## Documentation acceptance

A document is complete only when the intended successor can perform the documented task in a controlled environment
without undocumented assistance. Record the tester, date, environment, result, corrections, and final approver.
