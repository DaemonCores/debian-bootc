---
name: td-20261018-full-image-install-recommends
description: Main Containerfile's package install omits `--no-install-recommends`, unlike every other apt install in the repo.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Docker audit 0.8.2
      note: re-confirmed by Docker audit 0.8.2 at Containerfile:101 (layer hygiene); ID reused
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-full-image-install-recommends

- **Area**: Infra
- **Category**: docker
- **Severity**: Low
- **Status**: Confirmed by user
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
Phase 3 of `Containerfile` runs `apt install -y` for ~50 packages without `--no-install-recommends`. Phases 1/3.1 of the same file, `Containerfile.minimal` and `Containerfile.iso` all pass the flag. Apt list cleanup is handled globally by `99-apt-clean`, so that part of the baseline is satisfied.

## Impact
Recommends pulled in by ~50 packages add unreviewed packages and size to the OS image, and to every ostree update delta. Users cannot tell whether the difference from the minimal image is intentional.

## Where (pointers)
- `Containerfile:101` — `apt install -y` without --no-install-recommends
- `Containerfile:58` — same file uses the flag in Phase 1
- `Containerfile.minimal:181` — minimal image uses the flag
- `src/debianpreinstall/etc/apt/apt.conf.d/99-apt-clean:1` — lists cleanup via DPkg::Post-Invoke

## Suggested direction
Add `--no-install-recommends` and list any genuinely wanted recommends explicitly. If pulling recommends is intended for the 'full' flavour, say so in a comment and in docs/justifications.md.

## Next step
`create ticket`
