# ACMAD ClimWeb Executive Project Achievement Report and Forward Plan

## Document purpose and reporting scope

This report presents a comprehensive executive account of what the ACMAD ClimWeb project has achieved, the value
created for ACMAD and its users, the repository and documentation evidence supporting those achievements, and the
next outcomes that should be pursued. It is an achievement and forward-planning report rather than a technical
inventory or an acceptance checklist.

The inherited ClimWeb repository begins on 3 February 2023. For consistent measurement, this report uses 6 August
2026—the point at which scheduled ACMAD product-import work first appears in the available repository history—as the
ACMAD implementation baseline. The reporting cut-off is 27 October 2026. Where production confirmation is still
needed, the report distinguishes an implemented repository capability from a service independently verified in the
running environment.

## Executive summary

The project has developed ClimWeb into an integrated digital-service platform for ACMAD. The work brings together
automated climate-product publication, Regional Climate Centre services, specialised programme sites, public
communications, subscriptions and notifications, institutional content, event and application workflows, staff and
HR operations, and the technical foundations required to deploy, secure, monitor, back up, and maintain the service.

The central achievement is not a single website redesign. It is the establishment of a shared operating platform in
which scientific products, programme communications, institutional information, public engagement, and internal
workflows can be managed through one governed content and service environment. This reduces repeated manual work,
supports more timely publication, improves traceability, and gives ACMAD staff greater editorial and operational
control.

Available repository evidence records 548 unique commits and 167 pull-request merge commits across all available
references between the ACMAD implementation baseline and the reporting cut-off. The activity spans three connected
delivery waves: product automation and public-platform foundations in August; RCC services, data workflows, events,
and ENSO expansion in September; and programme consolidation, staff operations, integrations, and documentation in
October. Commit volume is included only as evidence of delivery scale; the achievements themselves are described by
capability and outcome below.

The next phase should concentrate on operational consolidation: verifying the exact deployed service, completing
end-to-end testing of priority workflows, reconciling migrated content, confirming institutional ownership of
accounts and external services, rehearsing recovery, training each user group, and establishing a measured roadmap
for continued improvement.

## Delivery evidence at a glance

| Evidence | Recorded result | What it demonstrates |
| --- | ---: | --- |
| Inherited repository history | From 3 February 2023 | The wider platform history on which the ACMAD work was built |
| ACMAD implementation reporting baseline | 6 August 2026 | Consistent starting point for the ACMAD delivery analysis |
| Reporting cut-off | 27 October 2026 | Date to which the evidence and achievements were reviewed |
| Unique commits across available references since baseline | 548 | Scale of implementation activity across integrated and continuing work |
| Pull-request merge commits since baseline | 167 | Evidence of repeated review and integration activity |
| Initial documentation expansion | 25 files and 2,409 added lines | Breadth of operational, editorial, technical, and continuity guidance produced |
| Primary evidence sources | Git history, application modules, configuration, tests, and project guides | Traceable basis for the achievement statements in this report |

## Project evolution and delivery approach

The project evolved the inherited ClimWeb and Wagtail foundation through incremental feature branches and reviewed
integration work. This allowed product operations, RCC services, programme sites, staff workflows, and infrastructure
changes to develop in parallel while continuing to use shared platform services such as authentication, search,
content management, task queues, storage, and deployment configuration.

The delivery approach consistently combined three layers:

- public experiences for visitors, partners, applicants, subscribers, and scientific users;
- controlled interfaces for editors, product operators, programme teams, HR reviewers, and administrators; and
- background services for imports, schedules, notifications, file handling, integrations, backup, and deployment.

That layered approach is important because it turns visible pages into maintainable services. A product catalogue,
for example, is backed by import configuration, task execution, progress information, publication history,
subscriptions, and operator documentation—not only by a public page.

## Comprehensive account of achievements

### Climate-product migration and automated publication

The project created a reusable framework for importing historical products and publishing new products on a schedule.
The framework supports configurable source locations, product-specific parsing, controlled task execution, progress
and failure information, stop and retry actions, publication history, and operator-facing configuration. This work
moves a substantial portion of product administration away from repeated manual uploading and toward observable,
repeatable workflows.

Product coverage developed across ACMAD and RCC families, including dekadal and monthly bulletins, policy briefs,
atmospheric analysis, heat-stress products, ITD and ITCZ monitoring, thunderstorm and nowcasting material, climate and
health products, seasonal forecasts, monthly climate products, onset products, climate-change material, annual
climate products, Climate Watch outputs, rainfall exceedance, cryosphere monitoring, five-day rainfall, seasonal
verification, and model-performance products.

The operational value created includes faster publication, more consistent metadata, clearer source provenance,
reduced repetition, and a shared method for extending the catalogue to future product families. The supporting guides
explain the migration model and the importer controls [R1, R2].

### Product subscriptions, notifications, and audience reach

The project extended product publication into an audience service. Users can subscribe to relevant product updates,
manage their interests through a subscriber dashboard, receive notification emails, and unsubscribe through a
controlled process. Subscription information was expanded to support sector and organisation context, and authorised
staff can export subscriber records for analysis and engagement activities.

Notification templates, product validity and descriptive information, and publication-triggered delivery improve
the usefulness of alerts. Together, these capabilities enable ACMAD to build a more direct relationship with users of
its climate services and to understand demand across sectors. The design and operational workflow are documented in
the subscription and notification guide [R3].

### Regional Climate Centre digital service

The RCC implementation established a coherent digital destination rather than a collection of disconnected pages.
It includes a dedicated landing experience, RCC navigation, product and data-service catalogues, climate monitoring
resources, training and coordination content, long-range forecasting material, and programme-specific presentation
and routing.

Data-oriented work includes ARC2 storage and imports across multiple countries, country and station browsing, CPC
rainfall data, seasonal forecast maps, EIN15, climate indices, reference climatologies, Climate Watch information,
Climsoft resources, and monitoring interfaces. Long-range forecasting forums and galleries, capacity-development
content, and coordination information broaden the RCC service beyond file distribution.

The result is a stronger foundation for ACMAD's RCC mandate: scientific information can be organised by service and
geography, updated through defined workflows, and presented through a recognisable RCC environment. Editorial and
operational instructions are consolidated in the RCC management guide [R4].

### Africa-focused ENSO information service

The project created an Africa-focused El Niño–Southern Oscillation experience that combines current information with
explanatory and contextual content. It includes a thematic landing page, bulletin presentation, an ENSO explanation,
an explainer image, related news and events, partner activities, homepage integration, pagination, and mobile
presentation refinements.

This gives non-specialist and specialist audiences a clearer route from the climate phenomenon to its African
relevance, current ACMAD information, and related institutional activity. It also gives editors a structured way to
maintain the service as conditions and bulletins change. The content model and editor workflow are documented in the
ENSO management guide [R5].

### CLIMSA programme presence

The project delivered a dedicated CLIMSA programme site within the shared platform. The implementation includes a
programme homepage, navigation, About content, output and product presentation, publication selection, news and
events, programme-specific interface treatments, and subdomain configuration.

This creates a distinct public identity for CLIMSA while retaining shared publishing, infrastructure, search, and
maintenance capabilities. Programme staff can present results and updates without operating a separate technology
stack. The CLIMSA guide records the principal content and management workflows [R6].

### Summer School information and application experience

The Summer School work created a richer programme and participation experience. Achievements include dedicated
edition pages, homepage promotion, application opening and deadline controls, manual closing, an online-joining call
to action, daily activities, participant-facing information, reviews, galleries, and improved news and media
presentation.

These capabilities support the full communication cycle—from promotion and application through delivery and
post-event storytelling. Explicit deadline and closure behavior also reduces ambiguity for applicants and programme
staff. The editor and programme workflow is documented in the Summer School management guide [R7].

### Public homepage and service discovery

The public homepage was redesigned into a configurable institutional front door. Work includes configurable visual
themes, a product carousel, featured-product ordering, news and events presentation, service and partner sections,
the Director General's message, an African RCC map, and a directory of African national meteorological and
hydrological services.

Editors gained control over more homepage selections and ordering without requiring a code deployment. Visitors gain
clearer entry points into products, programmes, events, institutional information, and continental services. This
work strengthens both everyday discoverability and ACMAD's presentation as a regional institution.

### Institutional information and governance content

The project expanded the site's institutional record through a Director General profile, Board of Governors content,
an organisational timeline with supporting documents, service and organisation-page improvements, GIS application
links, and configurable institutional content.

These additions make governance, leadership, history, and service responsibilities easier to find and maintain. They
also reduce reliance on static page layouts by giving authorised editors structured management controls. Relevant
editor workflows are described in the institutional-content guide [R8].

### News, publications, galleries, and media presentation

Public communications were strengthened through improved news and event presentation, publication metadata,
multilingual publication support, video and gallery components, quotation blocks, and richer media handling. These
features allow ACMAD to communicate scientific work, institutional activity, partnerships, and programme outcomes in
formats better suited to different audiences.

The result is a broader editorial toolkit and more consistent reuse of media across the site. The media and news
management guide provides supporting instructions [R9].

### Event migration, registration, and collaboration services

The project introduced tools to migrate ACMAD event records, download associated images and documents, preserve
unpublished material where appropriate, sanitise or repair imported HTML, and present events through an updated
public experience. Registration workflows gained clearer closing-date enforcement and improved export handling.

Google Meet and Calendar integration enables authorised event workflows to create and communicate online meeting
details through institutional services. These changes connect event publishing, participation, collaboration, and
record management more effectively than a standalone event listing.

### Forms and controlled data collection

General form behavior was improved through deadline handling, closed-state presentation, validation refinements, and
background ZIP exports for larger response sets. The same principle was applied to programme and event application
flows: users receive a clear state, while staff have more reliable controls over collection and export.

This supports time-bound calls, registrations, surveys, applications, and other institutional data-collection needs
without requiring a separate form platform for each activity.

### Staff profiles and secure account lifecycle

The project developed invitation-only staff profiles with secure setup, links to existing accounts, self-service
updates, review and publication, bulk invitations and reminders, protected portraits, and formal offboarding. Public
staff presentation is therefore connected to a controlled internal identity and review process rather than managed as
unrelated page content.

The account lifecycle reduces unmanaged access and gives staff responsibility for maintaining their information while
retaining institutional oversight. Detailed workflows, roles, and controls are documented in the staff workspace
guide [R10].

### Staff workspace, activities, reports, and HR review

Beyond profiles, the project created a staff operations workspace. It supports activity assignment, training and
report workflows, multiple supporting documents, submission and review, workflow notifications, authorised downloads,
bulk staff actions, and HR oversight.

This consolidates recurring internal processes that would otherwise be spread across email, shared folders, and
individual records. It also creates a foundation for clearer activity history, reporting accountability, and
management follow-up. Because these workflows involve personal and operational information, protected storage and
role-based access were incorporated into the design [R10].

### Google Shared Drive and institutional integrations

Google Shared Drive integration supports controlled creation or use of staff folders and synchronisation of report
documents when the integration is enabled. Together with Google Meet and Calendar support, this connects ClimWeb
workflows to institutional collaboration tools while keeping the platform as the operational point of reference.

The value is continuity and reduced duplication: staff can work with familiar institutional storage and meeting
services while workflow state remains visible in ClimWeb. Configuration, account ownership, and operating procedures
for Drive are documented separately [R11].

### Deployment, multi-site routing, and release foundations

The repository now defines development and production Docker profiles, PostgreSQL with PostGIS, Redis, Celery workers
and scheduling, nginx routing, and configuration for the main site and programme subdomains. Deployment guidance
covers environment preparation, application services, static and media handling, database migrations, and controlled
release activities [R13, R14].

Subdomain and TLS guidance supports distinct public identities for services such as RCC and CLIMSA without creating
independent application estates. This shared architecture reduces duplicated operational overhead while preserving
clear public routing [R14, R15].

### Security, privacy, backup, and operational continuity

Public authentication exposure was reduced, sensitive staff material was separated from ordinary public media, and
role and access guidance was expanded. Backup and restore procedures address application data and media, while
monitoring guidance identifies the services, queues, schedules, storage, and public routes that operators should
observe [R16, R17].

Disaster-recovery, release-management, access-transfer, and content-migration guidance now provide a stronger basis
for continuity beyond the original implementation team [R17, R18, R19]. These measures do not remove the need for
regular exercises; they establish the documented method by which ACMAD can operate and test continuity.

### Documentation and knowledge transfer

The project produced a structured set of product, programme, editorial, staff, infrastructure, release, and
continuity guides under the `docs/` tree. The documentation covers routine use as well as higher-risk activities such
as deployment, TLS, backup, restore, access transfer, release management, and content reconciliation.

This documentation is itself a major project outcome. It converts implementation knowledge into institutional
knowledge, gives different user groups task-specific instructions, and provides stable reference points for training,
maintenance, and future procurement or enhancement work. A repository-evidence snapshot and detailed project report
supplement this executive report [R20, R21, R22].

## Outcomes and value created

### More timely and repeatable climate services

Automated importers, scheduling, progress visibility, and publication history reduce the effort needed to keep product
collections current. Operators have a common pattern for managing varied data sources, and users have clearer access
to product families and updates.

### Stronger public and stakeholder engagement

Subscriptions, improved email notifications, programme sites, richer events, structured institutional information,
and better media presentation give ACMAD more direct and varied ways to serve users, partners, applicants, and the
public.

### Greater editorial independence

Configurable homepage content, structured programme pages, product controls, media components, and Wagtail-based
workflows allow authorised staff to manage significantly more of the public service without requiring a software
release for routine changes.

### An integrated programme platform

RCC, ENSO, CLIMSA, Summer School, public institutional content, and staff services use shared infrastructure and
platform capabilities. This reduces fragmentation and creates a clearer basis for common governance, security,
monitoring, and support.

### Improved internal process visibility

Invitation-based staff accounts, activity assignments, reports, reviews, notifications, and controlled documents
turn previously dispersed interactions into visible workflows with defined roles and status.

### Better maintainability and continuity

Containerised environments, task queues, multi-site routing, operational guides, recovery procedures, and a broad
documentation set make the platform easier for a successor team to understand, operate, and extend.

## Delivery progression

| Period | Delivery emphasis | Principal achievements |
| --- | --- | --- |
| 6–31 August 2026 | Product automation and public-platform foundations | ACMAD importers; importer monitoring and schedules; product subscriptions; homepage redesign; RCC landing service; staff-profile workflows; form controls; institutional-content improvements |
| September 2026 | RCC, data services, events, and thematic expansion | RCC datasets and importers; climate indices and climatologies; training and coordination content; subdomain and TLS work; event migration; Google Meet support; Board content; OJT and participant mapping; Africa-focused ENSO service |
| 1–27 October 2026 | Programme consolidation, internal operations, and continuity | ENSO refinements; CLIMSA programme site; Summer School enhancements; configurable editorial controls; staff and HR workspace; Google Drive support; leadership and media improvements; operational and project documentation |

## Evidence and reference register

The references below point to version-controlled project guides and evidence records. Paths are relative to the
repository root and can be reviewed alongside the implementation history.

| Ref. | Evidence or guide | Principal coverage |
| --- | --- | --- |
| R1 | `docs/_docs/products/acmad-product-migrations.md` | Historical product migration scope, commands, and validation |
| R2 | `docs/_docs/products/product-importer-feature.md` | Import configuration, scheduling, progress, retries, and operations |
| R3 | `docs/_docs/products/product-subscriptions-and-notifications.md` | Subscriber workflow, notification delivery, exports, and unsubscribe behavior |
| R4 | `docs/_docs/manage_pages/Manage-RCC.md` | RCC pages, datasets, service content, and operator workflows |
| R5 | `docs/_docs/manage_pages/Manage-ENSO.md` | ENSO content structure and editorial management |
| R6 | `docs/_docs/manage_pages/Manage-CLIMSA.md` | CLIMSA programme content and management |
| R7 | `docs/_docs/manage_pages/Manage-Summer-School.md` | Summer School content, applications, activities, and media |
| R8 | `docs/_docs/manage_pages/Manage-Institutional-Content.md` | Leadership, governance, timeline, organisation, and service content |
| R9 | `docs/_docs/manage_pages/Manage-News-and-Media.md` | News, galleries, video, quotations, and media workflows |
| R10 | `docs/_docs/manage_settings/Manage-Staff-Workspace.md` | Staff accounts, profiles, activities, reports, HR review, and offboarding |
| R11 | `docs/_docs/manage_settings/Manage-Staff-Google-Drive.md` | Shared Drive configuration, folder ownership, and report synchronisation |
| R12 | `docs/_docs/technical/acmad-architecture.md` | Application components, dependencies, data flows, and trust boundaries |
| R13 | `docs/_docs/technical/deployment.md` | Development and production deployment workflow |
| R14 | `docs/_docs/technical/subdomain-deployment.md` | Main-site and programme subdomain routing |
| R15 | `docs/_docs/technical/tls-certificates.md` | TLS certificate provisioning, renewal, and verification |
| R16 | `docs/_docs/technical/operations-monitoring.md` | Service health, queues, schedules, logs, storage, and alerts |
| R17 | `docs/_docs/technical/disaster-recovery.md` | Backup coverage, restoration, recovery roles, and exercises |
| R18 | `docs/_docs/technical/release-management.md` | Release preparation, verification, rollback, and records |
| R19 | `docs/_docs/technical/content-migration-acceptance.md` | Content reconciliation, evidence, exceptions, and owner review |
| R20 | `docs/_docs/technical/handover/repository-evidence-2026-10-27.md` | Reproducible repository evidence at the reporting cut-off |
| R21 | `docs/_docs/technical/handover/project-handover-report.md` | Detailed project scope, achievement register, open work, and evidence needs |
| R22 | `docs/_docs/technical/handover/operations-command-runbook.md` | Safe operational commands for discovery, testing, deployment, backup, and recovery |

## Next steps and forward delivery plan

The next phase should protect the value already created and convert the implemented capabilities into consistently
measured operations. Actions are grouped by desired outcome rather than by document completion.

### 0–30 days: establish a verified operational baseline

- Record the deployed application version, active services, database migration state, workers, scheduler, domains,
  TLS status, storage locations, and backup jobs in one controlled operational record.
- Run and record priority end-to-end journeys: public browsing, representative product imports, publication,
  subscription and notification, event registration, Summer School application, staff invitation, staff reporting,
  HR review, and protected-file access.
- Triage the existing application test failures and establish a repeatable test baseline for the exact version chosen
  for ongoing operations.
- Confirm institutional owners and deputies for hosting, source control, DNS, TLS, email, Google services, monitoring,
  analytics, external product sources, and backup storage.
- Review privileged accounts, remove obsolete access, verify multifactor authentication and recovery, and rotate any
  credential whose custody is uncertain.
- Publish the reviewed documentation and make it accessible to technical, editorial, programme, product, and HR
  users.

### 31–60 days: complete content, recovery, and user adoption

- Reconcile migrated products, datasets, events, publications, news, programme content, staff records, media, and
  institutional pages against agreed source counts and named content owners [R19].
- Exercise an isolated restoration of the database, public media, private staff documents, and critical configuration;
  record actual recovery times, gaps, and corrective actions [R17].
- Validate importer schedules and source reliability for every high-priority product family, including clear owner
  response when a source is late, unavailable, or changes format.
- Conduct role-based practical training for infrastructure operators, product operators, editors, programme teams,
  event administrators, HR reviewers, and account owners using real workflows.
- Confirm email delivery, bounce handling, subscription preferences, Google Meet and Calendar behavior, and Shared
  Drive ownership through controlled tests.
- Agree retention and deletion rules for applications, exports, subscriber records, staff reports, protected images,
  and operational logs.

### 61–90 days: stabilise service management

- Resolve the highest-impact defects and usability issues found through real operation, testing, training, and content
  review; maintain one prioritised backlog with owners, target dates, and verification criteria.
- Activate or refine monitoring for public availability, worker and scheduler health, importer failures, email
  delivery, certificate expiry, storage growth, database health, and backup completion [R16].
- Measure key service indicators such as product-publication timeliness, importer success rate, notification delivery,
  form completion, editorial turnaround, incident resolution, and restore performance.
- Establish regular permission reviews, inactive-account checks, backup verification, dependency updates, and content
  freshness reviews.
- Run a support and incident exercise so each responsible team knows how to identify, escalate, communicate, and
  resolve a service interruption.

### 3–6 months: improve capability and sustainability

- Use operational metrics and stakeholder feedback to prioritise improvements to product discovery, data access,
  mobile usability, multilingual content, accessibility, and subscriber segmentation.
- Reduce importer fragility by documenting source contracts, adding automated source checks, improving failure
  notifications, and maintaining representative test fixtures.
- Expand analytics around which products, regions, sectors, events, and programmes users engage with, while applying
  appropriate privacy controls.
- Review infrastructure capacity, database and media growth, task-queue throughput, email volume, and backup costs
  against actual usage.
- Formalise a release calendar, maintenance window, dependency-update routine, and quarterly recovery exercise.
- Maintain the documentation as part of each change: every new feature should include operator instructions, owner,
  monitoring expectations, test evidence, and recovery implications.

### Strategic opportunities beyond six months

- Develop a prioritised API and open-data roadmap for products that can be safely and sustainably provided to
  partners and researchers.
- Strengthen interoperability with regional and national climate-service systems through agreed metadata,
  identifiers, and exchange formats.
- Introduce service-level objectives for high-value product families and programme services once reliable baseline
  measurements are available.
- Use the shared platform to onboard future ACMAD programmes through reusable page types, governance standards, and
  common operational services rather than separate web estates.
- Establish a recurring user-research programme with national meteorological services, sector users, partners,
  applicants, and staff to guide evidence-based improvements.

## Conclusion

The ACMAD ClimWeb project has delivered a broad and connected digital capability. Its achievements span scientific
product operations, RCC data and services, thematic and programme communication, public engagement, institutional
content, event and application workflows, internal staff processes, external collaboration tools, and the
infrastructure and documentation needed to sustain them.

The most important next step is consolidation, not reinvention. ACMAD should verify the service as operated, embed
clear institutional ownership, complete content and recovery exercises, train each user group, measure performance,
and direct future development through a prioritised evidence-based roadmap. Doing so will turn the implementation
already achieved into a dependable and continuously improving institutional service.
