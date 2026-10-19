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

## ROCKNIX device patches (KT-18)

The mainline device patches of ROCKNIX are applied, as `module` class on
`arm64`. Each one was downloaded and tried against the pristine 7.2.11 tree
(`patch --dry-run`, then in order):

| Source directory | Patches | Result on 7.2.11 |
|------------------|---------|------------------|
| `mainline` | `0003` pwm_set_period, `0004` adc-keys, `0005` btrtl RTL8733BU | apply |
| `mainline-rockchip` | `001`, `002`, `005`-`008` (RK817 charger and bindings) | apply in order (`005` and `008` need the earlier ones) |
| `7.2` | `0010`-`0018` (Qualcomm MSM display, dispcc) | apply |
| `7.2` | `0011-thermal-adc-tm5-drop-iio-val-int-check` | already in the mainline tree, not listed |
| `7.2` | `9998` silence initramfs unpack warning | applies, `kernel` class (it edits `init/initramfs.c`, always built in) |
| `7.2` | `9999` fix Rust build error | does not apply to 7.2.11; it only renames the `tools/perf` Rust cross targets to ROCKNIX's own `*-rocknix-linux-*` triples, which a standard toolchain does not provide, so it would not help us anyway |

Every touched file is a `tristate` driver (`CHARGER_RK817`, `KEYBOARD_ADC`,
`BT_RTL`, `BT_HCIBTUSB`, `DRM_MSM`, `COMMON_CLK_QCOM`, `SM_DISPCC_*`) or a
header, hence the `module` class. The module build applies the `kernel` then the
`module` patches (`lib/kernel-prepare.sh`); the image build applies only the
`kernel` ones.

Not applied, with the reason:

- `devices/RK3588/patches/linux/*` (16 files): ROCKNIX applies them to the
  `armbian/linux-rockchip` `rk-6.1-rkr3` vendor tree, not to a kernel.org tree.
  They were not tried against 7.2.11.
- `raspberrypi/linux`: the project publishes a full kernel branch, not a patch
  series, so there is no patch file to list.

The `.config` side is separate: `kernel/modules/rpi5` enables `PCIE_BRCMSTB`,
`MISC_RP1`, `PINCTRL_RP1`, `COMMON_CLK_RP1` and `MACB` (the Cadence GEM inside
RP1); the former `BCMGENET` entry was wrong for the Pi 5. `kernel/modules/arm`
has `ROCKCHIP_DW_HDMI_QP` and `DRM_PANTHOR`. Symbols were checked against the
7.2.11 Kconfig files with `check_kconfig.py`. Not verified: that any board boots,
since no build on the runner or hardware test was run.
