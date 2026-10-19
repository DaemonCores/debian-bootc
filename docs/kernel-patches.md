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

## Current selection

| Patch | Source | Stage | Class | Why |
|-------|--------|-------|-------|-----|
| `bore` | CachyOS `sched/0001-bore.patch` | common | kernel | Scheduler core, cannot be a module. The only scheduler patch: BORE variants for other schedulers (`prjc`, `muqss`) compete with it and are not applied. |

XanMod is not applied: it is one monolithic patch that rewrites the same
scheduler, memory and I/O files as BORE, so it would collide with it. Its
individual optimisations are taken only when they exist as separate patches.
`bore-cachy` is not used on the current series: it is written against the
CachyOS tree and does not apply to a plain kernel.org tree.

## Rockchip and Raspberry Pi hardware (KT-18)

The device support that ROCKNIX and `raspberrypi/linux` carry for the boards we
target is already in the mainline 7.x tree, so no device patch is listed in
`kernel/patches.yml` for it. Everything is enabled as modules in the per-board
overlays, which keeps a single kernel:

- Raspberry Pi 5: the Ethernet, USB, I2C, SPI and UART are behind the RP1 chip
  on a PCIe link. `kernel/modules/rpi5` enables `PCIE_BRCMSTB`, `MISC_RP1`,
  `PINCTRL_RP1`, `COMMON_CLK_RP1` and `MACB` (the Cadence GEM inside RP1). The
  former `BCMGENET` entry was wrong for the Pi 5; GENET is the Pi 4 controller.
- RK3588: `ROCKCHIP_DW_HDMI_QP` and `DRM_PANTHOR` are already in
  `kernel/modules/arm`, and both symbols exist in 7.2.11.

All symbols were checked against the 7.2.11 Kconfig files with
`check_kconfig.py`. Not verified: that these boards boot, since no build or
hardware test was run. A device patch is only added here if a board still lacks
a driver once tested, and it follows the same module-or-kernel rule as above.
