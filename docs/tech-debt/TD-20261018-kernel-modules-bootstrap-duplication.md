---
name: td-20261018-kernel-modules-bootstrap-duplication
description: The ~70-line kernel-source bootstrap (find common deb, purge, apt-get source, ARCH translation, .config seed) is copy-pasted across three linux-modules-* build scripts in packages.yml.
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

# TD-20261018-kernel-modules-bootstrap-duplication

- **Area**: Backend
- **Category**: code-quality
- **Severity**: Medium
- **Status**: Fixed (not built; CI is the check)
- **Effort**: M
- **Blast radius**: local (1-2 files)

## Problem (fact)
The `build:` scripts of `linux-modules-arm`, `linux-modules-arm-device` and `linux-modules-x86_64` repeat the same steps line for line. Each one locates `linux-image-common_*_${DEB_ARCH}.deb` in `/tmp/prior`, purges the installed common deb, runs `apt-get source linux` and reinstalls the deb. Each also translates `ARCH` (amd64 → x86_64) and seeds `.config` from the common deb. `linux-modules-generic` repeats the `COMMON_DEB` lookup a fourth time. The copies have already drifted: the ARM note on `ARCH` is present at `:313-314` but missing from `:807-810`. The purge line `apt-get purge -y linux-image-common || dpkg --purge linux-image-common || true` is also copied three times and hides a failed purge.

## Impact
Fixes to this bootstrap are delicate and well documented (the linux-upstream pseudo-source and the modpost `__fentry__` failure), and each one must be applied 3–4 times by hand. If one copy is missed, a single device's module job breaks.

## Where (pointers)
- `workflows/bootc-debs-builder/packages.yml:292` — linux-modules-arm-device, the only entry left that sources `kernel_prepare`

## Suggested direction
Extract the bootstrap into one script, for example `workflows/bootc-debs-builder/preinstall/build/kernel-prepare.sh`, add it to each entry's `sources:` so it is hashed, and source it from each `build:` block.

## Next step
`create ticket`

## Resolution
The three identical bootstrap copies (linux-modules-arm, linux-modules-arm-device, linux-modules-x86_64) now source `workflows/bootc-debs-builder/lib/kernel-prepare.sh` and call `kernel_prepare`. Verified before the change that the 28 command lines of the three copies were identical. The script is listed in each entry's `sources:` and in the shell gate, and a test checks that. The `linux-modules-generic` COMMON_DEB lookup and the `|| true` purge chain are unchanged; the purge still hides a failed purge. Not built: the CI module jobs are the real check.

Later change: the `linux-modules-arm`, `linux-modules-x86_64` and `linux-modules-generic` entries no longer exist (their overlays moved into the kernel build), so only `linux-modules-arm-device` still sources `kernel_prepare`.
