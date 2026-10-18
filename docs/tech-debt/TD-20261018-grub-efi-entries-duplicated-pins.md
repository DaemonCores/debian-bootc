---
name: td-20261018-grub-efi-entries-duplicated-pins
description: grub-efi-amd64-signed and grub-efi-arm64-signed duplicate the GRUB version/branch/commit pins and most of their build script.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Code-quality audit
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-grub-efi-entries-duplicated-pins

- **Area**: Backend
- **Category**: code-quality
- **Severity**: Low
- **Status**: Confirmed by user
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`GRUB_VER`, `GRUB_FEDORA_BRANCH` and `GRUB_PINNED_COMMIT` are declared with the same values in both GRUB entries. The clone, checkout, bootstrap, configure and make steps are also mirrored, differing mainly in `--target` and the output paths. The arm64 entry is introduced as one that "mirrors grub-efi-amd64-signed".

## Impact
A GRUB bump or security pin change has to be made in two places. If one is missed, amd64 and arm64 ship different GRUB builds under the same `GRUB_VER` label.

## Where (pointers)
- `workflows/bootc-debs-builder/packages.yml:975-977` — amd64 pins
- `workflows/bootc-debs-builder/packages.yml:1149-1151` — identical arm64 pins
- `workflows/bootc-debs-builder/packages.yml:1140-1142` — 'mirrors grub-efi-amd64-signed'

## Suggested direction
Use one entry parameterised on `dpkg --print-architecture` (target and EFI suffix), or move the shared build into a sourced script that holds a single pin.

## Next step
`create ticket`
