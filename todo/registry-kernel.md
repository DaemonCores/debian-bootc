# Registry — kernel-modules (linux-image-common + per-device overlays)

Grep-markable point registry for the kernel common/overlay refactor. Working
ref (plan/todo); NEVER git-committed.

The disk is the territory — every STATUS flip is proven by a command.

<!-- BEGIN P01 -->
### P01 — Create registry
- REQ (verbatim): "Read kernel/config-x86_64, kernel/config-rpi3, config-rpi4, config-rpi5, config-rk3588"
- STATE (by command, 2026-08-01):
  - `ls kernel/` → config-rk3588 config-rpi3 config-rpi4 config-rpi5 config-x86_64 (5 fragments).
  - All 5 fragments read this session (read tool calls above).
  - Intersection (command, sorted `^CONFIG_`): shared by ALL 5 = EXT4_FS=y, XFS_FS=y, BTRFS_FS=y, TMPFS=y, VIRTIO_PCI=y, VIRTIO_BLK=y, VIRTIO_NET (4 y + 1 m in x86_64), and the 6 disables (SOUND/DRM/BT/WIRELESS/CFG80211/MAC80211).
- DECISION: Write this registry. Proceed to P02-P05.
- STATUS: ✅ DONE
  - Proof: this file exists; `grep -c 'BEGIN P0' todo/registry-kernel.md` → 5.
<!-- END P01 -->

<!-- BEGIN P02 -->
### P02 — Create kernel/config-common (base for linux-image-common)
- REQ (verbatim): "Redesign: create kernel/config-common with options shared by ALL devices (filesystems ext4/xfs/btrfs/tmpfs, virtio, basic networking, serial console). This is the base config for linux-image-common."
- STATE (by command, 2026-08-01):
  - `ls kernel/config-common` → absent (pre-state).
- DECISION: Create `kernel/config-common` holding ONLY the intersection of all 5 fragments: filesystems (ext4/xfs/btrfs/tmpfs built-in), virtio (PCI/BLK/NET built-in), the shared disable set (SOUND/DRM/BT/WIRELESS/CFG80211/MAC80211), plus the shared serial-console primitives that EVERY device needs for early boot (8250 + AMBA PL011 + their _CONSOLE — both serial families appear across the 5 devices, built-in so early-boot panics are never lost). VIRTIO_NET built-in (was m only in x86_64 — the task says "basic networking" in common; built-in avoids an initramfs module race for the bootc fetch path; x86_64 keeps its NIC drivers as modules in the overlay). All options built-in (=y) to match the existing convention (the prior fragments built everything in except a few x86_64 NIC/USB drivers as modules).
  EXTENSION (task: "basic networking, cgroups, namespaces"): added explicit
  networking core (NET, INET, UNIX, PACKET), cgroups v2 + 8 controllers
  (CGROUPS, CGROUP_BPF, CGROUP_FREEZERER, CPUSETS, CGROUP_DEVICE,
  CGROUP_SCHED, CGROUP_PIDS, MEMCG, BLK_CGROUP), and namespaces (NAMESPACES,
  UTS_NS, IPC_NS, USER_NS, PID_NS, NET_NS). All =y, all default=y in modern
  defconfigs — restated so the common base is explicit and a downstream
  defconfig change cannot silently drop them. bootc + systemd + container
  runtimes (podman/runc) depend on every one of these.
- STATUS: ✅ DONE
  - Proof: `test -f kernel/config-common && echo OK` → OK.
  - `grep -cE '^CONFIG_' kernel/config-common` → 30 (was 12, now 30 after
    adding 18 networking/cgroup/namespace options).
  - fs/virtio/serial: 12 (as before).
  - networking: NET, INET, UNIX, PACKET = 4.
  - cgroups: CGROUPS + 8 controllers = 9.
  - namespaces: NAMESPACES + 5 _NS = 6. Total 12+4+9+6 = 31? No: 30 because
    CGROUPS is the core and the 8 controllers are separate = 9 cgroup lines,
    6 namespace lines (1 core + 5 _NS), 4 net lines, 12 fs/virtio/serial =
    31. Recheck: `grep -cE '^CONFIG_'` → 30 (CGROUP_BPF counted, 8 ctrl, see
    list above). Discrepancy is one off — recount: ext4,xfs,btrfs,tmpfs (4),
    virtio_pci,blk,net (3) = 7, 8250+console,pl011+console (4) = 11, net
    4 = 15, cgroups: CGROUPS+BPF+FREEZER+CPUSETS+DEVICE+SCHED+PIDS+MEMCG+BLK
    = 9 → 24, ns: NAMESPACES+UTS+IPC+USER+PID+NET = 6 → 30. Correct.
<!-- END P02 -->

<!-- BEGIN P03 -->
### P03 — Slim per-device overlays (config-<device> = ONLY device-specific)
- REQ (verbatim): "Per-device fragments (config-rpi3, config-rpi4, config-rpi5, config-rk3588, config-x86_64) keep ONLY device-specific options (SoC, Ethernet PHY, MMC, USB, RTC). They are applied as OVERLAYS on top of config-common."
- STATE (by command, 2026-08-01): each overlay file currently re-states the shared fs/virtio/disable block (duplication).
- DECISION: Rewrite each overlay to keep ONLY: (a) SoC platform (ARCH_BCM2835/2711/2712, ARCH_ROCKCHIP, none for x86_64), (b) device-specific serial console IF NOT already covered by common (PL011 is in common, so overlays no longer re-state it; x86_64 keeps 8250 already in common → overlay has NO serial), (c) device-specific MMC/SD, (d) device-specific Ethernet PHY driver, (e) device-specific USB host controllers, (f) device-specific RTC (rk3588 only), (g) x86_64-specific block storage (NVMe/AHCI) + NIC drivers as modules. Overlays are merged AFTER common via merge_config.sh, so a =m in the overlay overrides the common =y for the SAME symbol (kernel kconfig last-wins) — used deliberately for x86_64 to keep its physical-NIC and USB-HC drivers as modules (=m) per the original design, while the common virtio/net stays built-in for VMs.
- PLAN: rewrite config-x86_64, config-rpi3, config-rpi4, config-rpi5, config-rk3588.
- STATUS: ✅ DONE
  - Proof: zero overlap between config-common and each overlay.
    Method: `grep -E '^(CONFIG_|# CONFIG_)' kernel/config-common | sort` →
    /tmp/cc-cfg.txt; same for each overlay → /tmp/<dev>.txt; `grep -Fxf`
    common-overlay for each device → EMPTY (no shared line).
    Commands run (each returned empty = no overlap):
      grep -Fxf /tmp/cc-cfg.txt /tmp/r3.txt   (rpi3)
      grep -Fxf /tmp/cc-cfg.txt /tmp/r4.txt   (rpi4)
      grep -Fxf /tmp/cc-cfg.txt /tmp/r5.txt   (rpi5)
      grep -Fxf /tmp/cc-cfg.txt /tmp/rk.txt   (rk3588)
      grep -Fxf /tmp/cc-cfg.txt /tmp/x86.txt  (x86_64)
  - Per-device content (verified by read): rpi3 = ARCH_BCM2835 + MMC_BCM2835
    + BCMGENET. rpi4 = ARCH_BCM2711 + MMC_SDHCI(+PLTFM+BCM2835) + DWC3 + XHCI
    + BCMGENET. rpi5 = ARCH_BCM2712 + MMC_SDHCI(+PLTFM+BCM2835) + XHCI +
    BCMGENET. rk3588 = ARCH_ROCKCHIP + MMC_SDHCI(+PLTFM) + DWMAC_GENERIC +
    STMMAC_ETH + DWC3 + XHCI + EHCI + RTC_CLASS + RTC_DRV_PL031. x86_64 =
    BLK_DEV_NVME + SATA_AHCI + E1000/E1000E/IGB/R8169 (=m) + XHCI/EHCI (=m) +
    disables (USB_HID, INPUT_JOYSTICK, INPUT_TABLET). All common options
    (fs, virtio, serial, sound/drm/bt/wlan disables, networking, cgroups,
    namespaces) REMOVED from overlays — live only in config-common.
<!-- END P03 -->

<!-- BEGIN P04 -->
### P04 — Update packages.yml (linux-image-common + linux-modules-<device>)
- REQ (verbatim): "Update packages.yml: build ONE linux-image-common (from config-common), then per-device linux-modules-<device> (from config-<device> overlay). The modules package depends on linux-image-common. This saves N-1 kernel rebuilds."
- STATE (by command, 2026-08-01):
  - `grep -n 'linux-image' workflows/bootc-debs-builder/packages.yml` → one `linux-image` entry that loops over all fragments, doing a FULL `make bindeb-pkg` per device (N full kernel rebuilds).
- DECISION: Replace the single `linux-image` loop with TWO stages in ONE package entry (kept as `linux-image` so the `deb-glob` and `sources` hash stay stable, avoiding a wave-rewrite downstream):
  1. STAGE 1 (ONCE): merge config-common into defconfig, `make olddefconfig`, `make -j bindeb-pkg` → produce `linux-image-common_<ver>_<arch>.deb`. This is the ONE full kernel build.
  2. STAGE 2 (PER DEVICE, modules only): for each device fragment, `make mrproper` → start from defconfig → merge config-common THEN config-<device> → `make olddefconfig` → `make -j modules_install` into a DESTDIR → package the `/lib/modules/<ver>/...` tree as `linux-modules-<device>_<ver>_<arch>.deb`. The modules package `Depends: linux-image-common` (control template). N-1 full kernel rebuilds are saved (only modules are compiled per device, reusing the common kernel image).
  The `sources:` list is extended with `../../kernel/config-common`. The `deb-glob` becomes `linux-image-common_* linux-modules-*_*` (two globs) so the builder picks up both the common image deb and the per-device modules debs.
  NOTE on ver magic: STAGE 2 modules are built against the SAME kernel source + SAME config-common base + the device overlay, so their `vermagic` matches the common image's `vermagic` (the image deb carries the vmlinuz built in STAGE 1). The modules install into `/lib/modules/<ver>-common/` to match the common image's modules dir.
- PLAN: edit workflows/bootc-debs-builder/packages.yml.
- STATUS: ✅ DONE
  - Proof: `grep -n 'STAGE 1\|STAGE 2\|linux-image-common\|linux-modules-' workflows/bootc-debs-builder/packages.yml` → STAGE 1 (line ~112), STAGE 2 (line ~167), `cp ... /debs/linux-image-common_${BUILT_VER}_${ARCH}.deb` (154), `dpkg-deb --build ... /debs/linux-modules-${DEVICE}_${BUILT_VER}_${ARCH}.deb` (223).
  - `deb-glob:` line → `linux-image-common_* linux-modules-*_*` (line 70).
  - `sources:` includes `../../kernel/config-common` (line 77).
  - Modules control file `Depends: linux-image-common (= ${BUILT_VER})` (line 209).
  - Two-stage build: STAGE 1 `make -j bindeb-pkg` (130) ONCE; STAGE 2 per-overlay `make -j modules` (192) + `make modules_install` (201) — no vmlinuz rebuild per device.
<!-- END P04 -->

<!-- BEGIN P05 -->
### P05 — Build script: build common, then per-device modules only
- REQ (verbatim): "The build script: (1) build linux-image-common from config-common, (2) for each device, merge config-common + config-<device>, build only the MODULES (make modules_install), package as linux-modules-<device>."
- STATE: this is the build script inside packages.yml (P04). Same scope.
- DECISION: Implemented as part of P04's build script (two-stage). P05 is the script description; P04 is the packages.yml edit. They land in the same edit.
- STATUS: ✅ DONE
  - Proof: same as P04 — the build script in packages.yml (lines 88-232)
    implements STAGE 1 (`make bindeb-pkg` once) + STAGE 2 (`make modules` +
    `make modules_install` per overlay), exactly the two-stage flow the
    task describes.
<!-- END P05 -->