---
name: td-20261018-bootc-stack-behind-upstream
description: Pinned bootc stack versions in packages.yml trail upstream releases, and nothing automates bumps.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-bootc-stack-behind-upstream

- **Area**: Backend
- **Severity**: Low
- **Status**: Confirmed by user
- **Effort**: M
- **Blast radius**: module (5-10 files)

## Problem (fact)
`packages.yml` pins bootupd `v0.2.35` (upstream latest `v0.3.2`), bootc `v1.16.2` (latest `v1.17.1`) and ostree `2026.1` (latest `v2026.4`). composefs `v1.0.8` is current. bootupd also carries a local `bootupd-0.2.35-dpkg.patch`. Dependabot only covers `github-actions` and `docker`, not these manifest pins.

## Impact
Upstream fixes, including bootloader-update and security fixes, do not reach the image. The bootupd 0.2→0.3 jump grows while the version-specific dpkg patch must be rebased.

## Where (pointers)
- `workflows/bootc-debs-builder/packages.yml:1273` — BOOTUPD_VER v0.2.35
- `workflows/bootc-debs-builder/packages.yml:1404` — OSTREE_VER 2026.1
- `workflows/bootc-debs-builder/packages.yml:1472` — BOOTC_VER v1.16.2
- `workflows/bootc-debs-builder/patches/bootupd-0.2.35-dpkg.patch` — version-bound patch
- `.github/dependabot.yml` — no coverage of packages.yml pins
- Upstream tags checked 2026-10-18 via api.github.com/repos/{bootc-dev/bootc,ostreedev/ostree,coreos/bootupd,composefs/composefs}/releases/latest

## Suggested direction
Add a scheduled job or Renovate custom-regex manager for the `*_VER` pins, and plan the bootupd 0.3 upgrade, including whether the dpkg patch is still needed.

## Next step
`create ticket`
