# Kernel patch classification

The project kernel is the kernel.org tarball (see `docs/decisions.md`). Patches
from official sources (XanMod, CachyOS, ROCKNIX, raspberrypi/linux) are fetched
at build time and are never committed to this repository.

## Rule

Every patch is classified as **module** or **kernel**. There is one kernel and
no second build.

1. **A patch that can be a module is not applied to the kernel.** It ships as a
   module. When several competing variants of one function can all be modules,
   all of them ship as modules and each image loads the one it needs.
2. **A patch that cannot be a module is applied to the kernel.** When several
   variants compete, the best one for the minimal image is chosen and applied
   directly to the kernel.
3. **Mixing kernel and module patches is allowed; conflicts are not.** Two
   patches that change the same code and cannot coexist never ship together.
   The whole patch set must apply and build on the same tree without a
   collision.

A patch that does not apply is a hard build failure; the last-good published deb
is kept.

## Classification

Each patch in the manifest carries its class (`module` or `kernel`). Whether a
patch can be a module is checked by reading the patched sources, not assumed:
core scheduler and memory-management code, for example, is generally not
buildable as a module.
