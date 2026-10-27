# ACMAD Project Handover

This section is the controlled handover pack for ACMAD's ClimWeb implementation. It distinguishes verified repository
evidence from deployment claims that still require confirmation by an authorized system owner.

## Reporting boundary

- **Inherited platform history:** ClimWeb repository history begins on 3 February 2023.
- **ACMAD implementation baseline:** 6 August 2026, when ACMAD-specific product migration work first appears in the
  repository history.
- **Current audit date:** 27 October 2026.
- **Repository:** `ACMAD-Niamey/climweb`.
- **Default remote branch:** `origin/develop`.

The baseline must be approved in the final signed report. If the contract or project initiation document specifies a
different start date, update every report period and metric consistently.

## Handover documents

1. [Executive project achievement report](executive-handover-report.md) — comprehensive delivery achievements,
   supporting references, value created, and the forward delivery plan.
2. [Comprehensive project handover report](project-handover-report.md) — objectives, achievements, current state,
   risks, outstanding work, and evidence requirements.
3. [Operations command runbook](operations-command-runbook.md) — safe discovery, development, test, deployment,
   monitoring, backup, restoration, and release commands.
4. [Release and branch register](release-and-branch-register.md) — branch classification and the evidence needed to
   promote, retain, archive, or close each code line.
5. [Feature documentation register](feature-documentation-register.md) — documentation coverage, gaps, owners, and
   completion criteria.
6. [Access transfer and acceptance](access-and-acceptance-checklists.md) — account transfer, knowledge transfer,
   operational verification, and signatures.
7. [Repository evidence snapshot](repository-evidence-2026-10-27.md) — reproducible facts collected from locally
   available Git refs and repository configuration on the audit date.

## Rules for maintaining the pack

- Never place passwords, private keys, service-account JSON, recovery codes, or full environment files in Git.
- Record a credential's system, owner, successor, storage location, and verification status—not the credential itself.
- Do not label a feature "live" solely because code exists. Confirm the deployed commit and validate the public or
  protected workflow in the target environment.
- Every remaining action must have an owner, target date, dependency, and acceptance test.
- Update the branch register before every handover review and immediately after a release.
- Attach evidence by stable identifier: commit SHA, pull request, test result, approved URL, screenshot, migration log,
  backup identifier, or signed meeting record.

```{toctree}
---
maxdepth: 1
---
executive-handover-report
project-handover-report
operations-command-runbook
release-and-branch-register
feature-documentation-register
access-and-acceptance-checklists
repository-evidence-2026-10-27
```
