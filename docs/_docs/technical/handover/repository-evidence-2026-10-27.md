# Repository Evidence Snapshot — 27 October 2026

## Scope and limitations

This snapshot records evidence available from the local repository and its existing remote-tracking refs. No production
host, GitHub API, DNS account, email provider, Google Workspace, monitoring platform, or external content source was
queried. The remote-tracking refs were not refreshed from the network during this capture.

Do not interpret this snapshot as proof that a commit is deployed or a configured external service is operational.

## Baselines and history

| Evidence | Result |
| --- | --- |
| Earliest repository history | 3 February 2023 |
| ACMAD-specific implementation baseline used for reporting | 6 August 2026 |
| Unique commits across all locally available refs since baseline | 538 |
| Merge commits with messages beginning `Merge pull request` since baseline | 159 |
| Recorded `origin/develop` | `c79d0d06d701c8dbe31339709e2794891c000d0f` — PR #192, 20 October 2026 |
| Recorded `origin/production` | `eeb2f69936eec4d05041df061e8d729a09a9836a` — PR #183, 15 October 2026 |
| Initial `documentations` base | `7e5f02ba0044b352c9e6dee551e1c46acfec0bbc` — 22 October 2026 |
| Initial `origin/develop...documentations` divergence | 161 commits only on recorded develop; 4 commits only on documentation base |
| Corrected documentation candidate | Documentation-only commit applied to recorded `origin/develop`; divergence `0 1` |

The four feature commits unique to the documentation branch's base were:

1. `be2b8924` — Build CLIMSA website section.
2. `b7d1a6f8` — Refine CLIMSA programme homepage.
3. `af34f05c` — Build CLIMSA about page and refine programme UI.
4. `7e5f02ba` — Add daily activities and reviews to summer school.

The handover documents themselves were uncommitted at the initial capture and are not included in the initial divergence
counts. They were committed and the documentation-only delta was subsequently reapplied to the recorded integration
baseline as described above.

## Local branch containment

Containment tests used the recorded remote-tracking heads. An ancestor result proves only Git reachability.

### Integrated into recorded develop and production heads

`UI-modifications`, `acmad-staff`, `backup/ui-fixes-before-products-migration-fix-20261006`, `board-of-governors`,
`codex/disable-public-auth-pages`, `codex/rcc-website-before-develop-merge`, local `develop`, `el-nino-africa`,
`email-subscriptions`, `events-migrations`, `faq`, `fix/subscription-form`, `hero-carousel-mods`, local `production`,
`products-migrations`, and `rcc-website`.

### Integrated into recorded develop but not recorded production

| Branch | Tip | Evidence state |
| --- | --- | --- |
| `codex/summer-school-gallery` | `c6a2b83050dc` — Improve CUIP service page content | Integrated, not contained in production ref |
| `staff-dashboard-enhancements` | `b787d50ccc6b` — Add GIS applications to product pages | Integrated, not contained in production ref |

### Not contained in either recorded remote head

| Branch | Tip | Ahead of develop | Ahead of production | Review purpose |
| --- | --- | ---: | ---: | --- |
| `backup/rcc-before-drop-20260925` | `8b968d92d821` | 2 | 2 | Backup/supersession review |
| `backup/ui-fixes-before-cleanup-20261006` | `a02a2b95d069` | 3 | 3 | Backup/supersession review |
| `climsa-website` | `7e5f02ba0044` | 4 | 4 | Canonical CLIMSA branch decision |
| `codex/climsa-website-clean` | `3fbc296e4e1c` | 4 | 17 | Compare CLIMSA and RCC fixes |
| Initial `documentations` | `7e5f02ba0044` at capture | 4 | 4 | Resolved after capture by applying documentation-only commit to recorded integration baseline |
| `goole-meet-integration` | `3e890609600e` | 2 | 2 | Confirm integration or supersession |
| `ojt` | `498bf062a6d7` | 1 | 1 | Confirm delivery of HTML repair tooling |
| `summer-school-enhancement` | `a79f82e74c8f` | 13 | 26 | Review media/migration changes for integration |
| `ui-fixes` | `9f6826309692` | 3 | 13 | Review post-PR code and staff workspace guide |

## Integration-branch implementation inventory

The following inventory was read from `origin/develop`, not from the divergent working-tree branch.

### Compose services

Thirteen services are defined:

- Development: `climweb_db_dev`, `climweb_redis_dev`, `climweb_dev`, `climweb_celery_worker_dev`,
  `climweb_celery_beat_dev`, and `climweb_nginx`.
- Production: `climweb_db_prod`, `climweb_redis_prod`, `climweb_prod`, `climweb_celery_worker_prod`,
  `climweb_celery_beat_prod`, `climweb_acmad_seed_prod`, and `climweb_nginx_prod`.

Seven named volumes are defined: `static`, `media`, `private_exports`, `static_prod`, `media_prod`,
`private_exports_prod`, and `private_staff_reports_prod`.

### Code inventory

| Item | Filename-based count on `origin/develop` |
| --- | ---: |
| Executable management-command modules (excluding `__init__.py`) | 50 |
| Migration files matching numbered migration names | 422 |
| Test files matching repository test naming | 142 |

The command modules cover product bootstrap/imports, configured product imports, ENSO seeding, RCC subdomain and content
seeding, RCC resource/data synchronization, event import/repair, staff Drive checking, version reporting, form repair,
CMS upgrade reset, and participant seeding.

### Configuration-name inventory

The integration branch's sample environment includes names for:

- database, Redis, Django, host/CSRF, time zone, workers, static/media/backup volumes, and nginx/TLS paths;
- SMTP, newsletter, reCAPTCHA, Google Meet, and Google Drive;
- product-subscription rate limits;
- ACMAD importer enablement, intervals, and limits;
- RCC source-host restrictions.

Only names and documented defaults may be included in the handover. Values from real `.env`, GitHub secrets, service
accounts, or host configuration must be transferred through approved secure channels.

## CI/CD evidence

`.github/workflows/climweb-ci-cd.yml` records:

- push and pull-request triggers for `develop` and `production`;
- a test job;
- a deploy job restricted to a push on `production`;
- production deployment using the production checkout and Makefile/Compose lifecycle.

This confirms workflow intent, not a successful run for the eventual release SHA. Attach the actual CI run and deployed
SHA during acceptance.

## Documentation-location evidence

| Document | Recorded location at capture |
| --- | --- |
| Staff Google Drive guide | Present on `origin/develop` and `origin/production` |
| Staff workspace guide | Present on local `ui-fixes`; absent from recorded `origin/develop` |
| CLIMSA source audit | Present under `migration/climsa` in the working repository history |
| Deployment/subdomain/TLS guides | Present in technical documentation |
| Product importer, ACMAD migration, and subscription guides | Present in product/technical documentation |
| Comprehensive handover suite | Initially uncommitted at capture; committed and transferred to the corrected candidate afterward |

## Local validation results

| Validation | Result |
| --- | --- |
| `git diff --check` | Passed for current tracked changes at validation time |
| Handover files present | Passed |
| Trailing-whitespace scan | Passed |
| Full Docker test suite | Not run: local Docker daemon unavailable |
| Sphinx documentation build | Not run: Sphinx module unavailable in the selected runtime |
| Production smoke tests | Not run: no production access used |

## Working-tree control observation

At capture, the working tree also contained changes outside the new handover files: a modified `.gitignore`, a modified
CLIMSA CSS file, and untracked private-report and secret directories. Their contents were not inspected for this evidence
record. They must not be staged, committed, copied, or disclosed as part of the documentation change without explicit
review and authorization.

## Required next evidence

1. Refresh remote refs and rerun branch containment with authorized network access.
2. Run the full test suite and documentation build on the corrected candidate SHA.
3. Record the production SHA and service health from the authorized host.
4. Complete domain/TLS, migration, worker/scheduler, importer, email, Google, private-file, backup, and restore tests.
5. Populate owners, training records, migration counts, outstanding actions, and signatures.
