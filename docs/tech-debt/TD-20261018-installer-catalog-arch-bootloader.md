---
name: td-20261018-installer-catalog-arch-bootloader
description: gen-recipe.py lists amd64 and arm64 images on every ISO and hardcodes bootloader `grub2` for both.
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

# TD-20261018-installer-catalog-arch-bootloader

- **Area**: Other
- **Severity**: Low
- **Status**: Mitigated
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
The installer catalogue is generated with a fixed `arches = ["amd64", "arm64"]` and `"bootloader": "grub2"` for every entry, whatever the ISO's architecture. The arm64 images are built with `u-boot-tools` as `BOOT_PKG`. The script has no tests.

## Impact
A user booting the amd64 installer ISO is offered arm64 images that cannot run on that machine, and arm64 entries advertise a bootloader the image does not ship. Install fails late, after disk partitioning.

## Where (pointers)
- `src/buildisopreinstall/usr/libexec/debian-bootc/gen-recipe.py:33` — fixed arch list
- `src/buildisopreinstall/usr/libexec/debian-bootc/gen-recipe.py:46-56` — every entry gets bootloader grub2
- `Containerfile.iso:59-67` — generator invoked at ISO build with ARCH available but not passed
- `Containerfile:28-30` — BOOT_PKG differs per arch (grub vs u-boot-tools)

## Suggested direction
Pass `ARCH` to gen-recipe.py and emit only matching images, with the bootloader derived per arch. Add a small unit test for the generator.

## Next step
`create ticket`

## Resolution
`gen-recipe.py` reads `ARCH` and lists only images of that architecture; `Containerfile.iso` passes its `ARCH` build argument, and `tests/unit/test_gen_recipe.py` covers the filter. The per-arch `bootloader` value is unchanged (`grub2` for every entry): the values the installer accepts for the u-boot arm64 images are not documented in this repo, so that part stays open. Not yet verified by a real ISO build.
