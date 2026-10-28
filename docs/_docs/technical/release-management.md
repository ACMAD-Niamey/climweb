# Release and Branch Management

This guide defines how ACMAD changes move from feature work to `develop` and `production` without losing branch-only
migrations, documentation, or operational configuration.

## Canonical branches

- `develop`: integration target; pushes and pull requests run tests.
- `production`: release branch; a successful push test can trigger deployment.
- feature branches: short-lived, scoped work reviewed through a pull request.
- backup branches: temporary recovery evidence with an explicit owner and expiry; not informal release lines.

Confirm actual protections and workflow behavior in GitHub before relying on this policy.

## Before opening a pull request

1. Update from the agreed target without overwriting unrelated work.
2. Review unique commits and three-dot diff.
3. Resolve migration graph conflicts explicitly.
4. Update user, operator, configuration, backup, and release documentation.
5. Run tests and migration checks on the exact tip.
6. Identify environment names, volumes, tasks, DNS/TLS, external service, and data-migration effects.
7. Define acceptance and rollback/forward-fix plans.

Useful read-only commands:

```bash
git log origin/develop..FEATURE_BRANCH --oneline --decorate
git diff --stat origin/develop...FEATURE_BRANCH
git diff --name-status origin/develop...FEATURE_BRANCH
git merge-base origin/develop FEATURE_BRANCH
```

## Migration review

- List new migrations by app and dependency.
- Detect parallel numbering and merge migrations.
- Test from the current production database schema to the candidate.
- Test application startup, worker/beat registration, and representative old data.
- Document irreversible transformations and data backfills.
- Never resolve a conflict by deleting an unfamiliar migration without tracing deployed state.

## Release candidate gate

A candidate needs:

- approved pull requests and branch disposition;
- green CI for the exact SHA;
- clean migration checks;
- updated `.env.sample`/guides for new configuration names;
- reviewed persistent/private-data changes;
- pre-release backup and recovery plan;
- editor/operator acceptance steps;
- named deployer, reviewer, window, and communication owner.

## Production promotion

Use the protected pull-request/approval process. Record candidate SHA before merge, resulting production SHA, CI run,
deployment start/end, migrations, backups, service health, smoke tests, exceptions, and operator/reviewer.

Do not deploy feature branches directly as a substitute for promotion.

## Branch closure

Classify each branch as production, integrated, release candidate, active, blocked, superseded, archive, or close. Before
closing, record tip SHA, pull request, unique commits, migration/content evidence, documentation, deployment state, and
approver. Confirm no required commits or documents exist only on that branch.

## Emergency changes

Use a narrowly scoped branch from the verified production head, review/test it, promote through production, then merge
the resulting fix back into `develop`. Record why the normal schedule was bypassed. Avoid direct unreviewed server edits;
if an emergency host change is unavoidable, capture and reconcile it into version control immediately afterward.
