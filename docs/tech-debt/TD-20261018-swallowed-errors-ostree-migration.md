---
name: td-20261018-swallowed-errors-ostree-migration
description: `&& ... || true &&` chains in the ostree migration swallow failures of every earlier command, not just the intended `cp`.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Code-quality audit
      note: re-confirmed by focused code-quality audit
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-swallowed-errors-ostree-migration

- **Area**: Infra
- **Category**: code-quality
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
Bash parses `mkdir -p ... && cp -r ... || true && rm -rf ...` as `((mkdir && cp) || true) && rm ...`. A failing `mkdir` of `/var/home`, `/var/roothome` or `/sysroot/ostree` is ignored and the build continues to delete `/home` and `/root` and create dangling symlinks.

## Impact
A broken ostree layout is not caught at build time. It surfaces only later at QEMU test, `bootc install` or upgrade, defeating the `-euo pipefail` SHELL the files set.

## Where (pointers)
- `Containerfile:172-179` — mkdir/cp chain ending in `|| true`
- `Containerfile.minimal:264-271` — same pattern
- `Containerfile:51` — strict SHELL that this bypasses

## Suggested direction
Scope the tolerance to the copy only: `&& { cp -r /usr/lib/locale/* /var/usr/lib/locale/ || true; } &&`, or test that the source glob is non-empty before copying.

## Resolution (commit c083560)
Changed `&& cp -r /usr/lib/locale/* /var/usr/lib/locale/ || true \` to `&& { cp -r /usr/lib/locale/* /var/usr/lib/locale/ || true; } \` in both `Containerfile` and `Containerfile.minimal`. The `|| true` now only catches the cp failure (source glob empty or copy error); a failing mkdir now exits the build under `set -euo pipefail` as intended.
