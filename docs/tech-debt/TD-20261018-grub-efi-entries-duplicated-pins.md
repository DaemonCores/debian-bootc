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
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`GRUB_VER`, `GRUB_FEDORA_BRANCH` and `GRUB_PINNED_COMMIT` are declared with the same values in both GRUB entries. The clone, checkout, bootstrap, configure and make steps are also mirrored, differing mainly in `--target` and the output paths. The arm64 entry is introduced as one that "mirrors grub-efi-amd64-signed".

## Impact
A GRUB bump or security pin change has to be made in two places. If one is missed, amd64 and arm64 ship different GRUB builds under the same `GRUB_VER` label.

## Where (pointers)
- `workflows/bootc-debs-builder/packages.yml:811-687` — amd64 pins
- `workflows/bootc-debs-builder/packages.yml:985-861` — identical arm64 pins
- `workflows/bootc-debs-builder/packages.yml:976-852` — 'mirrors grub-efi-amd64-signed'

## Suggested direction
Use one entry parameterised on `dpkg --print-architecture` (target and EFI suffix), or move the shared build into a sourced script that holds a single pin.

## Next step
`create ticket`

## Resolution
Resolved by removing the unconsumed arm64 entry (see [TD-20261018-grub-efi-arm64-unconsumed](TD-20261018-grub-efi-arm64-unconsumed.md)): a single `grub-efi-amd64-signed` entry now holds the GRUB pins, so there is nothing left to keep in sync. The parity test added earlier is deleted with it.

The arm64 entry was restored later, because generic arm64 machines need the Fedora GRUB too. Both entries now carry no pin at all: each tracks the head of the `rhboot/grub2` default branch through `track:` (see [decisions](../decisions.md)), so there is no pin left to keep in sync. They still share the same source and differ only in target and output paths.
