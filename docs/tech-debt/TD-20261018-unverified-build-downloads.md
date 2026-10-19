---
name: td-20261018-unverified-build-downloads
description: Build recipes fetch toolchains and the OSTree source tarball over the network without checksum or version pinning.
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

# TD-20261018-unverified-build-downloads

- **Area**: Security
- **Category**: security
- **Severity**: Medium
- **Status**: Fixed
- **Effort**: M
- **Blast radius**: module (5-10 files)

## Problem (fact)
The buildenv recipe downloads `yq` from `releases/latest`, resolves `gh` from the `releases/latest` API, and pipes `sh.rustup.rs` into `sh`, all without a checksum. In `packages.yml`, the OSTree release tarball is piped straight into `tar` with no `sha256sum -c`, while the bootupd and bootc downloads are checksum-verified.

## Impact
A compromised or changed upstream artifact enters the build environment, or the shipped `ostree` package, which is part of the boot path, without detection. `latest` resolution also makes buildenv rebuilds non-reproducible: a monthly rebuild can silently pick up a breaking yq/gh major version.

## Where (pointers)
- `workflows/env.yml:74-83` — yq from releases/latest, no checksum
- `workflows/env.yml:89-97` — gh version resolved from releases/latest, no checksum
- `workflows/env.yml:99-102` — `curl https://sh.rustup.rs | sh`
- `workflows/bootc-debs-builder/packages.yml:1537-1413` — ostree tarball piped to tar, no checksum
- `workflows/bootc-debs-builder/packages.yml:1417-1295` — bootupd download IS checksum-verified (contrast)
- `workflows/bootc-debs-builder/packages.yml:1609-1487` — bootc download IS checksum-verified (contrast)

## Suggested direction
Pin yq/gh/rustup-init versions with per-arch SHA-256 values in env.yml, as is already done for `BOOTC_GPG_SHA256`. Add an `OSTREE_SHA256` env var and `sha256sum -c` to the ostree build, following the bootupd/bootc pattern.

## Next step
`create ticket`

## Resolution
`workflows/env.yml` now pins yq (v4.54.1), gh (v2.102.0) and rustup-init (1.29.1, from the versioned `rustup/archive` path instead of `sh.rustup.rs`) with per-arch SHA-256 checked by `sha256sum -c`. `workflows/bootc-debs-builder/packages.yml` downloads the OSTree tarball to a file and checks `OSTREE_SHA256` before extraction, like bootupd and bootc. The digests come from the GitHub release API and the rustup `.sha256` files. Not yet exercised by a real buildenv or ostree build; bumping a version now requires updating its digest.
