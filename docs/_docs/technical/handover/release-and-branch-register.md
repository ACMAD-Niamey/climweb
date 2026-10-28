# Release and Branch Register

## Snapshot

Snapshot date: **27 October 2026**. Refresh this page immediately before review or release.

| Reference | Recorded tip | Interpretation |
| --- | --- | --- |
| `origin/develop` | `c79d0d06` — PR #192, 20 October 2026 | Remote default and integration baseline at audit time |
| `origin/production` | `eeb2f699` — PR #183, 15 October 2026 | Repository production reference; running host still requires verification |
| `documentations` candidate | 27 October 2026 corrected candidate | Documentation-only commit applied to recorded `origin/develop`; exactly one commit ahead at correction time |

## Containment summary

| Relationship at capture | Local branch count | Interpretation |
| --- | ---: | --- |
| Ancestor of both `origin/develop` and `origin/production` | 16 | History is contained in both recorded remote heads |
| Ancestor of `origin/develop`, not `origin/production` | 2 | Integrated but not contained in the recorded production ref |
| Ancestor of neither recorded remote head | 9 | Requires review; may be active, divergent, superseded, backup, or documentation work |

The two develop-only local branches were `codex/summer-school-gallery` and `staff-dashboard-enhancements`.

## Branches requiring disposition

These local branches were not reachable from `origin/develop` at the audit date. "Requires disposition" does not mean
all are intended for merge; backup or superseded branches may instead need an evidence-preserving archive decision.

| Branch | Tip date | Tip subject | Required decision |
| --- | --- | --- | --- |
| `climsa-website` | 22 Oct | Add daily activities and reviews to summer school | Select canonical CLIMSA/Summer School history; compare with clean and enhancement branches |
| `codex/climsa-website-clean` | 22 Oct | Fix RCC navigation context | Determine whether its fixes are present in the canonical branch |
| `summer-school-enhancement` | 22 Oct | Expand news body video embeds | Review migrations/media blocks and integrate approved work |
| `ui-fixes` | 21 Oct | Document staff workspace operations | Promote approved post-PR work and canonical staff documentation |
| `goole-meet-integration` | 14 Sep | Merge Google connection into Meet settings | Confirm supersession or integrate; preserve the existing misspelled branch name in references |
| `ojt` | 4 Sep | Add event HTML repair command | Confirm whether the command/content repair was delivered elsewhere |
| `backup/rcc-before-drop-20260925` | 25 Sep | Restore omitted RCC titles | Retain only under an approved backup/archive policy |
| `backup/ui-fixes-before-cleanup-20261006` | 6 Oct | Refine service navigation and visibility | Verify that all wanted changes exist elsewhere, then archive or retain |

At the audit date, several branches were also not reachable from `origin/production`, including CLIMSA, Summer School,
staff-dashboard, and UI work. Recompute this list before the handover is signed.

## Refresh commands

```bash
git fetch --all --prune
git branch --all --no-color
git branch --no-merged origin/develop
git branch --no-merged origin/production
git log -1 --date=iso-strict --pretty=fuller origin/develop
git log -1 --date=iso-strict --pretty=fuller origin/production
```

For each candidate branch:

```bash
git log origin/develop..BRANCH --oneline --decorate
git diff --stat origin/develop...BRANCH
git diff --name-status origin/develop...BRANCH
git merge-base origin/develop BRANCH
```

## Required classification

Assign exactly one classification to every relevant branch:

- **Production:** reachable from the verified deployed production SHA.
- **Integrated:** merged to the agreed integration branch but not verified in production.
- **Release candidate:** approved and tested, awaiting promotion.
- **Active:** current work with a named owner and target.
- **Blocked:** retained work with a documented dependency and owner.
- **Superseded:** functionality exists in another identified branch or commit.
- **Archive:** evidence or recovery line not intended for integration.
- **Close:** safe to remove only after its tip and disposition are recorded and any required remote protections observed.

## Per-branch evidence template

| Field | Required value |
| --- | --- |
| Branch | Exact ref name |
| Tip SHA/date | Full SHA and authored/committed dates |
| Owner | Current responsible person |
| Purpose | Business and technical scope |
| Pull request | URL/number or reason no PR exists |
| Target | Integration/release branch |
| Unique commits | Reviewed list or range |
| Migrations | Names, ordering, conflict analysis |
| Configuration | Environment, service, volume, DNS, TLS, or secret-name changes |
| Tests | Exact command and result for tip SHA |
| Documentation | Guides changed or still required |
| Deployment state | Evidence, not assumption |
| Decision | Classification and approver |
| Follow-up | Owner, target date, acceptance test |

## Release gate

A branch is ready for promotion only when:

- unique commits and diffs have been reviewed;
- migration graph and data transformations are safe;
- tests pass on the exact candidate SHA;
- new configuration keys are documented without secret values;
- persistent data and private-file impacts are understood;
- editor/operator documentation is updated;
- backup and rollback plans are approved;
- target-environment smoke tests and an acceptance owner are defined.

The corrected documentation candidate has a documentation-only diff against the recorded integration baseline. Refresh
remote refs and repeat that check before merge. Existing CSS, secret-directory, private-report, or other unrelated
working-tree changes must not be included accidentally.
