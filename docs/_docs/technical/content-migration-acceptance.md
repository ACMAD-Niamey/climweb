# Content Migration and Acceptance

This guide applies to ACMAD products, RCC resources, institutional pages, staff profiles, events, Summer School, CLIMSA, news, publications, documents, images, redirects, and other legacy content.

## Migration ledger

Create one row per collection/batch with:

| Field | Purpose |
| --- | --- |
| Source | System, URL/export, owner, extraction date |
| Scope | Content type, language, period, expected count |
| Transformation | Mapping, cleanup, taxonomy, filename/date rules |
| Destination | Page type, parent, category, storage, hostname |
| Result | Created, updated, skipped, duplicate, rejected, missing counts |
| Exceptions | Missing files, invalid metadata, broken links, licensing/privacy decisions |
| Evidence | Command/run ID, log, sample URLs, checksum/report |
| Approval | Business reviewer, technical reviewer, date, conditions |

Never report only "migration completed" without counts and exceptions.

## Preparation

1. Freeze and identify the source snapshot.
2. Back up the destination.
3. Approve taxonomy, page hierarchy, languages, redirects, and duplicate policy.
4. Classify personal/confidential material before extraction.
5. Inventory documents/images separately from page records.
6. Test mappings and idempotency in a non-production environment.

## Execution

- Use repeatable scripts/commands rather than manual copying for large collections.
- Preserve source identifiers/provenance where supported.
- Log without exposing secrets or personal data.
- Make re-runs idempotent or document duplicate-prevention behavior.
- Keep rejected/missing records in an exception file with owners.
- Do not publish automatically unless the acceptance plan authorizes it.

## Reconciliation

For every batch verify:

```text
expected = created + updated/matched + skipped + rejected + missing
```

Define categories so records are not double-counted. Compare source and destination counts, dates, languages, documents,
images, parent relationships, taxonomy, publication state, and redirects.

## Sampling

Use risk-based samples including oldest/newest records, every language, every product/page type, items with multiple
documents/media, missing optional fields, unusual characters, external links, private records, and known source defects.

## Acceptance tests

- Correct page type, hierarchy, title, slug, date, language, and publication state.
- Accurate body, summary, metadata, taxonomy, and related content.
- Documents/images open, have correct type/title, and are not duplicated.
- Private data remains protected and excluded from public search/media.
- Redirects resolve to canonical destinations without loops.
- Search, filters, pagination, feeds, cards, and homepage/programme curation behave correctly.
- Mobile/accessibility checks pass for representative migrated content.
- Re-running the migration produces the documented idempotent result.

## Rollback and correction

Before execution, decide how migrated records are identified and reversed without deleting unrelated editor work. Prefer
corrective/idempotent reruns over manual mass deletion. Any destructive rollback requires explicit approval, verified
backup, exact target selection, and post-action reconciliation.

## Closure

A collection closes only when counts reconcile, exceptions have owners, redirects and media are tested, business and
technical reviewers sign, and remaining source systems have an approved retention/decommission plan.
