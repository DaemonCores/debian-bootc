---
name: td-20261018-reusable-workflow-main-ref
description: CI calls shared DaemonCores-CI workflows at the moving `@main` ref with `secrets: inherit` and write/id-token permissions.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Security audit 0.8.2
      note: re-confirmed at cited lines; ID reused, no slug change
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-reusable-workflow-main-ref

- **Area**: CI
- **Category**: security
- **Severity**: Medium
- **Status**: Confirmed by user
- **Effort**: M
- **Blast radius**: module (5-10 files)

## Problem (fact)
Both workflows delegate to `DaemonCores/DaemonCores-CI/...@main`, a moving branch, and pass `secrets: inherit`. The pipeline grants `contents`, `packages`, `pages`, `issues`, `actions` write and `id-token: ***REDACTED***`.

## Impact
Any push to DaemonCores-CI `main` immediately runs with this repo's secrets (SB_SIGNING_KEY / SB_SIGNING_CERT used by the GRUB build, MODULE_SIGNING_KEY) and can produce cosign-signed images through the OIDC identity. Builds are also not reproducible against a fixed pipeline definition. `docs/justifications.md` records this as a known trade-off.

## Where (pointers)
- `.github/workflows/pipeline.yml:57-63` — broad write + id-token permissions
- `.github/workflows/pipeline.yml:71` — `uses: ...full-pipeline.yml@main`
- `.github/workflows/pipeline.yml:84` — `secrets: inherit`
- `.github/workflows/docs-wiki-sync.yml:11` — `uses: ...docs-wiki-sync.yml@main`
- `.github/workflows/docs-wiki-sync.yml:14` — `secrets: inherit`
- `docs/justifications.md:59-63` — trade-off acknowledged

## Suggested direction
Pin the shared workflows to a tag or commit SHA and let Dependabot (github-actions ecosystem, already configured) bump it. Pass only the named secrets each stage needs instead of `inherit`.

## Next step
`create ticket`
