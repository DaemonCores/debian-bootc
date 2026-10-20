---
name: td-20261018-grub-efi-arm64-unconsumed
description: grub-efi-arm64-signed is built and signed but no Containerfile in this repo installs it; arm64 images use u-boot-tools.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Inferred
      reviewer: Code-quality audit
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-grub-efi-arm64-unconsumed

- **Area**: Backend
- **Category**: code-quality
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`packages.yml` builds and Secure-Boot-signs `grub-efi-arm64-signed`. No file in this repo references the package outside its own manifest entry and `preinstall/output/` control files. Both Containerfiles state that arm64 uses `u-boot-tools` instead of `grub-efi-arm64`. `bootc-finalize` stages only x64 shim/GRUB binaries.

## Impact
If nothing consumes it, a full GRUB compile and signing run on every cache miss is dead build code, and its pins must still be kept in sync (see [TD-20261018-grub-efi-entries-duplicated-pins](TD-20261018-grub-efi-entries-duplicated-pins.md)).

## Where (pointers)
- `workflows/bootc-debs-builder/packages.yml:977` — entry
- `Containerfile:28-30` — arm64 uses u-boot-tools via BOOT_PKG
- `Containerfile.minimal:13-14` — 'arm64 uses u-boot-tools instead of grub-efi-arm64'
- `workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:50` — only grub-efi-amd64-signed queried


## Suggested direction
If the package has no consumer, remove the entry. If one exists, document it in the entry's comment.

## Next step
`ask user`

## Resolution
Superseded (2026-10-19): bootupd 0.3 refuses to install without a `grub2` component, and the project requires every GRUB to come from the signed Fedora build. The `grub-efi-arm64-signed` package is restored and now consumed: arm64 images install it through `BOOT_PKG` next to `u-boot-tools` and hold it through `APT_HOLD_PKG`.
