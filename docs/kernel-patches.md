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
| `rocknix-btrtl-rtl8733bu` | ROCKNIX `mainline/0005-Bluetooth-btrtl-Add-the-support-for-RTL8733BU.patch` | arm64 | module | Adds the USB ID `0bda:b733` to `btusb` and the chip to `btrtl`, both tristate. |

XanMod is not applied: it is one monolithic patch that rewrites the same
scheduler, memory and I/O files as BORE, so it would collide with it. Its
individual optimisations are taken only when they exist as separate patches.
`bore-cachy` is not used on the current series: it is written against the
CachyOS tree and does not apply to a plain kernel.org tree.

## Patch triage against the project targets (KT-18)

The targets are the Raspberry Pi 3/4/5, the Rockchip RK3588, x86_64 and generic
ARM (`docs/glossary.md`, SBC targets). Every patch of the ROCKNIX mainline
directories (`mainline`, `mainline-rockchip`, `7.2`) and of the CachyOS `7.2/misc`
directory was downloaded and tried on the pristine 7.2.11 tree, then judged
against those targets. A patch that applies is not kept for that reason alone.

### Kept

- `rocknix-btrtl-rtl8733bu`: a generic USB Bluetooth adapter ID, useful on every
  target (see the table above).

### Removed after the check

| Patch | Why it is not useful here |
|-------|---------------------------|
| ROCKNIX `mainline/0003-pwm-add-pwm_set_period` | Adds a helper that nothing in the 7.2.11 tree calls. |
| ROCKNIX `mainline/0004-input-adc-keys-redirect-keycode-316-to-rocknix-joypa` | Exports a global `joypad_input_g` for ROCKNIX's out-of-tree joypad driver; no code of ours uses it. |
| ROCKNIX `mainline-rockchip/001`, `002`, `005`-`008` (RK817) | No RK3588 board of the tree uses the RK817 PMIC; the boards that do are RK3326, RK3566 and RK3568 handhelds. |
| ROCKNIX `7.2/0010`-`0018` (Qualcomm MSM, dispcc) | They fix SM8250/SM8550 display code; no Qualcomm board is a target. |
| ROCKNIX `7.2/9998-silence-initramfs-unpack-warn` | Lowers the "Initramfs unpacking failed" message from `KERN_EMERG` to `KERN_DEBUG`, which hides a boot failure we want to see. |

### Not applied

- ROCKNIX `7.2/0011-thermal-adc-tm5-drop-iio-val-int-check`: already in 7.2.11.
- ROCKNIX `7.2/9999-fix-rust-build-error`: does not apply, and only renames the
  `tools/perf` Rust cross targets to ROCKNIX's own triples.
- ROCKNIX `devices/RK3588/patches/linux/*` (16 files): written for
  `armbian/linux-rockchip` `rk-6.1-rkr3`, a 6.1 vendor tree, not for kernel.org.
- `raspberrypi/linux`: a full kernel branch, not a patch series.
- CachyOS `misc/0001-handheld.patch`: applies after BORE and does not overlap
  with the Bluetooth patch, but it enables x86 handheld consoles (Steam Deck and
  similar) and none is a target. It edits ACPI, power management and `amdgpu`
  core code, so it would be a kernel patch. Re-add it if such a device becomes a
  target.
- CachyOS `misc/0001-hardened.patch`: does not apply on 7.2.11 after BORE.
- CachyOS `misc/0001-rt-i915.patch` (PREEMPT_RT i915), `0001-acpi-call.patch`
  (an x86 debug module) and `0001-aufs-*.patch` (a new filesystem; the image uses
  ostree): no target needs them.
- CachyOS `misc/nvidia` and `dkms-clang.patch`: not read.

### NPU for inference (KT-19)

The RK3588 declares three NPU cores (`rockchip,rk3588-rknn-core` in
`rk3588-base.dtsi`) that the mainline Rocket driver
(`CONFIG_DRM_ACCEL_ROCKET`, `drivers/accel/rocket`) drives, so no patch is
needed. `kernel/modules/rk3588` enables it as a module and `kernel/config`
enables its bool framework `CONFIG_DRM_ACCEL`. `CONFIG_ROCKCHIP_IOMMU=y` comes
from the arm64 defconfig.

### Hardware config (RP1, RK3588)

`kernel/modules/rpi5` enables `PCIE_BRCMSTB`, `MISC_RP1`, `PINCTRL_RP1`,
`COMMON_CLK_RP1` and `MACB` (the Cadence GEM inside RP1); the former `BCMGENET`
entry was wrong for the Pi 5. `kernel/modules/arm` has `ROCKCHIP_DW_HDMI_QP` and
`DRM_PANTHOR`. All symbols were checked against the 7.2.11 Kconfig files with
`check_kconfig.py`.

Not verified: that any board boots, that `make olddefconfig` keeps
`DRM_ACCEL_ROCKET` (it could not run in the local environment; the Kconfig
source promotes a bool under a modular dependency to `y`, `scripts/kconfig/symbol.c`),
and that the Rocket driver works with the Mesa userspace on a real board.

## Inference-oriented kernel options (KT-19)

Added to `workflows/bootc-debs-builder/kernel/config` without measurement
(decision of the maintainer); only userspace and hardware compatibility was
checked.

| Option | Choice | Compatibility check |
| --- | --- | --- |
| Preemption model | `PREEMPT_LAZY` (default) | `PREEMPT_NONE` needs `ARCH_NO_PREEMPT` and `PREEMPT_VOLUNTARY` needs `!ARCH_HAS_PREEMPT_LAZY`; both x86_64 and arm64 select `ARCH_HAS_PREEMPT_LAZY`, so lazy is the throughput-oriented model available. Per `kernel/Kconfig.preempt` |
| `TRANSPARENT_HUGEPAGE` | on, `MADVISE` default | madvise only: no memory growth for processes that do not ask; userspace unchanged |
| `LRU_GEN`, `LRU_GEN_ENABLED` | on | `mm/Kconfig`: depends on `MMU` and 64-bit; no userspace interface change |
| `ZRAM` | module | inert until configured |
| `ZSWAP` | built in, off by default | `ZSWAP_DEFAULT_ON` stays unset |

### Rejected: 16 KB pages on arm64

`ARM64_16K_PAGES` is **not** enabled. The kernel is a single image for
Raspberry Pi 3/4/5, RK3588 and generic ARM. Raspberry Pi 3 (Cortex-A53) and
Pi 4 (Cortex-A72) are, to my knowledge, ARMv8.0 cores without the optional
16 KB translation granule, so such a kernel would not boot there. This is
from memory of the core manuals and was not checked against them or on
hardware. Even where the CPU supports it, `arch/arm64/Kconfig` notes that
AArch32 applications must be built with 16 KB-aligned segments, and a 16 KB
kernel would change the page size seen by every userspace on the shared
image. A page-size split would need a second kernel, which the single-kernel
decision (KT-13) rules out.

Not verified: the kernel was not built or booted with these options;
`make olddefconfig` cannot run on the current host, so symbol resolution is
justified from the Kconfig sources of 7.2.11 only.
