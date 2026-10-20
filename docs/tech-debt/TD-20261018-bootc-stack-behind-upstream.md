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
- **Status**: Mitigated (rolling releases implemented; first CI build pending)
- **Effort**: M
- **Blast radius**: module (5-10 files)

## Problem (fact)
`packages.yml` pins bootupd `v0.2.35` (upstream latest `v0.3.2`), bootc `v1.16.2` (latest `v1.17.1`) and ostree `2026.1` (latest `v2026.4`). composefs `v1.0.8` is current. bootupd also carries a local `bootupd-0.2.35-dpkg.patch`. Dependabot only covers `github-actions` and `docker`, not these manifest pins.

## Impact
Upstream fixes, including bootloader-update and security fixes, do not reach the image. The bootupd 0.2→0.3 jump grows while the version-specific dpkg patch must be rebased.

## Where (pointers)
- `workflows/bootc-debs-builder/packages.yml:1107` — BOOTUPD_VER v0.2.35
- `workflows/bootc-debs-builder/packages.yml:1238` — OSTREE_VER 2026.1
- `workflows/bootc-debs-builder/packages.yml:1306` — BOOTC_VER v1.16.2
- `workflows/bootc-debs-builder/patches/bootupd-dpkg.patch` — formerly version-bound, rebased on v0.3.2
- `.github/dependabot.yml` — no coverage of packages.yml pins
- Upstream tags checked 2026-10-18 via api.github.com/repos/{bootc-dev/bootc,ostreedev/ostree,coreos/bootupd,composefs/composefs}/releases/latest

## Suggested direction
Add a scheduled job or Renovate custom-regex manager for the `*_VER` pins, and plan the bootupd 0.3 upgrade, including whether the dpkg patch is still needed.

## Next step
`create ticket`

## Resolution
The boot-stack packages no longer pin a version. Each of `bootupd`, `bootc`, `ostree` and `libcomposefs` lists a `track:` entry in `workflows/bootc-debs-builder/packages.yml`; the shared `DaemonCores-CI/upstream-track` action resolves the latest GitHub release (tag and the SHA-256 of the vendor/source tarball, taken from the release API) before each build, and the resolved values feed the content hash. A release that does not build leaves the last-good published deb in place and opens a broken-build issue (existing `build-deb` behaviour), so a bad upstream release cannot break the image. The weekly `.github/workflows/upstream-check.yml` (reusable check in DaemonCores-CI, `--strict`) fails when a tracked package is still published on an older release.

The version-bound patch became `patches/bootupd-dpkg.patch` and was rebased on bootupd `v0.3.2` (the 0.2.35 patch no longer applied: `git apply --check` failed). The rebased patch was only applied and read, not compiled: this environment has no usable C toolchain, so the first compile and the `query_files_dpkg` unit test run in the CI build. Until that build passes, bootupd stays on its last published release (0.2.35). The resolver is unit tested in DaemonCores-CI (`tests/test_upstream_track.py`, file:// stub of the API); the live GitHub path and the workflows have not run on GitHub yet.
