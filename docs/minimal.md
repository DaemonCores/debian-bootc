# Minimal Images Documentation

## Overview

The `debian-bootc-minimal` variants are ultra-lean bootc/ostree images derived
from the same Debian Trixie base as the main `debian-bootc` image, but trimmed
to a bare bootable minimum. The goal is **< 10 MB RAM at idle** on a system
with no workload running.

The two variants are:

- **`Containerfile.minimal.x86_64`** — for VMs and bare-metal x86_64 hosts.
- **`Containerfile.minimal.arm64`** — a single multi-SBC image for the most
  common ARM64 single-board computers (Raspberry Pi 3/4/5, Rockchip,
  Allwinner, Amlogic).

Both images share the same bootc/ostree/composefs/dracut stack as the main
image. They intentionally omit:

- the SSH server (use the serial console, or add `openssh-server` in a
  downstream layer),
- man pages and the `man-db` rebuild timer,
- `bash-completion`, `nano`, `less` and other interactive niceties,
- `ifupdown2` (replaced by the lighter `systemd-networkd`),
- DKMS, kernel headers, and microcode packages,
- persistent logging (`journald` is set to `Storage=none`).

The result is an image small enough to run on SBCs with 512 MB of RAM and
fast enough to reach `multi-user.target` in well under 10 s on modern
hardware.

### Kernel packages are rolling, not pinned

Both minimal images install the Debian meta-packages `linux-image-amd64`
(x86_64) and `linux-image-arm64` (arm64). These meta-packages always track
the latest Debian kernel for the suite (`trixie`) and are **not** pinned to
a specific upstream version. Each image rebuild picks up whatever version
the meta-package currently points to. This is intentional (security updates
flow automatically) but means that two rebuilds a few weeks apart can ship
different kernel versions. If reproducibility matters, pin the kernel
explicitly in a downstream layer (`apt install linux-image-6.12.22-1-amd64`)
or build a custom kernel from the fragments in `kernel/` (see
[How to recompile the kernel](#how-to-recompile-the-kernel)).

## Architecture Support

### x86_64

Target hosts:

- Virtual machines (libvirt / qemu / KVM, VMware, VirtualBox).
- Bare metal x86_64 servers and workstations with a UEFI firmware.

Boot path:

- UEFI firmware → shim → GRUB (BLS) → dracut initramfs → ostree rootfs.

The image installs `grub-efi-amd64` from the debian-bootc APT repository
(the Fedora rhboot fork with `blscfg` / `blsuki` modules required by
bootc/ostree). The `bootc`, `dracut` and `grub-efi-amd64` packages all
come from the **third-party APT repository** at
`https://daemoncores.github.io/debian-bootc/` (referenced by
`src/bootcpreinstall/etc/apt/sources.list.d/debian-bootc.sources`). The
signing key for that repository is fetched and SHA-256-pinned in the
Containerfile (`BOOTC_GPG_SHA256`). Nothing in the minimal images is
installed from an unverified source.

### ARM64

A single `linux-image-arm64` kernel is used. It ships with all the upstream
device trees integrated, so it boots on a wide range of SBCs without
per-board kernel builds:

| SoC family        | Boards (examples)                                  |
|-------------------|----------------------------------------------------|
| BCM2837 / BCM2710 | Raspberry Pi 3 / 3B+                               |
| BCM2711           | Raspberry Pi 4 / 4B / 400                          |
| BCM2712           | Raspberry Pi 5                                     |
| Rockchip RK3399   | Pinebook Pro, RockPro64, Orange Pi RK3399          |
| Rockchip RK3568   | Radxa Zero3, Orange Pi 3B                           |
| Rockchip RK3588   | Orange Pi 5, Radxa Rock 5                          |
| Allwinner H6       | Orange Pi One Plus, Pine H64                       |
| Allwinner H616     | Orange Pi Zero2, various TV boxes                  |
| Amlogic S905       | Odroid C2, LibreTech CC                             |
| Amlogic S922X      | Odroid N2                                          |
| Amlogic SM1        | Odroid C4                                          |

Boot path:

- U-Boot on the board → either (a) directly loads the kernel + DTB, or
  (b) chains through the EFI shim + GRUB when the board firmware supports
  UEFI.

The image installs `u-boot-tools` (for `mkimage`, `fw_printenv`,
`fw_setenv`) instead of GRUB. A downstream layer that targets a UEFI
ARM64 server can install `grub-efi-arm64`.

#### Kernel command line on U-Boot SBCs

Most ARM64 SBCs boot through U-Boot, not GRUB. On those boards the kernel
command line is **not** read from `/etc/default/grub` — GRUB is not in the
boot path. The cmdline must instead be set in one of:

- the U-Boot environment (`fw_setenv bootargs '...'` / `setenv bootargs`
  at the U-Boot prompt), or
- the `chosen/bootargs` node of the device tree blob passed to the kernel,
  or
- a `boot.scr` / `extlinux.conf` file on the boot partition.

The `/etc/default/grub` `GRUB_CMDLINE_LINUX_DEFAULT` line written by
`Containerfile.minimal.arm64` Phase 6 only applies to boards that chain
through a UEFI GRUB (typically ARM64 servers, or SBCs running a UEFI
firmware like EDK2). For the common U-Boot SBC case, adjust the cmdline in
the U-Boot env or DTB instead. The default cmdline shipped by the image
includes several serial consoles (`ttyAMA0`, `ttyS0`, `ttyAML0`) so that
early-boot output appears on the UART regardless of which SoC the board
uses; the kernel silently ignores consoles that do not exist.

## Package List by Image

The table below compares the package set installed by each minimal image.
Packages not listed here are pulled in as dependencies by `apt`; only
top-level explicitly installed packages are shown.

| Package               | x86_64 | arm64 | Purpose                                                            |
|-----------------------|:------:|:-----:|--------------------------------------------------------------------|
| `linux-image-amd64`   |   x    |       | Debian generic AMD64 kernel                                       |
| `linux-image-arm64`   |        |   x   | Debian generic ARM64 kernel with all upstream DTBs                 |
| `firmware-linux-free` |        |   x   | DFSG-free firmware blobs needed by some ARM64 SBC peripherals      |
| `firmware-misc-nonfree` |      |   x   | Minimal non-free blobs (Amlogic GX, some Rockchip peripherals)     |
| `bootc`               |   x    |   x   | Atomic OS management on top of ostree                             |
| `dracut`              |   x    |   x   | Initramfs generator with native bootc/ostree/lvm modules           |
| `grub-efi-amd64`      |   x    |       | Fedora rhboot GRUB fork with BLS modules for bootc                |
| `u-boot-tools`        |        |   x   | `mkimage` / `fw_printenv` / `fw_setenv` for ARM64 SBC bootloaders  |
| `iproute2`            |   x    |   x   | The `ip` command, for network debugging and boot scripts          |
| `systemd-networkd`   |   x    |   x   | Native systemd network manager (replaces `ifupdown2`) (shipped by `systemd`, not a separate package)             |
| `systemd-timesyncd`  |   x    |   x   | NTP client (repacked with network-online drop-in)                 |
| `ca-certificates`     |   x    |   x   | Root CAs for HTTPS to APT / registries                            |
| `openssl`             |   x    |   x   | Crypto used by apt transport and bootc                            |
| `git`                 |   x    |   x   | Required by the bootc postinst hook                              |
| `curl`                |   x    |   x   | Fetch the bootc APT signing key                                    |
| `wget`                |   x    |   x   | Fetch the bootc APT signing key (fallback)                        |

Packages present in the **main** image but **deliberately omitted** from
both minimal images:

`dkms`, `linux-headers-*`, `firmware-linux` (full nonfree metapackage),
`intel-microcode`, `amd64-microcode`, `podman`, `adduser`, `sudo`,
`locales`, `console-setup`, `console-data`, `bash-completion`, `less`,
`man-db`, `nano`, `groff-base`, `manpages`, `libnss-systemd`,
`util-linux-extra`, `btrfs-progs`, `file`, `traceroute`, `lsof`, `bzip2`,
`xz-utils`, `apt-listchanges`, `bind9-host`, `bind9-dnsutils`, `perl`,
`wtmpdb`, `media-types`, `liblockfile-bin`, `openssh-server`,
`openssh-client`, `reportbug`, `debian-faq`, `krb5-locales`,
`inetutils-telnet`, `netcat-traditional`, `doc-debian`, `dbus`,
`ifupdown2`, `openresolv`, `dhcpcd`, `isc-dhcp-client`, `wpasupplicant`,
`broadcom-sta-dkms`, `firstboot-user-setup`.

## Disabled Services

The following systemd units are **masked** (not just disabled) in both
minimal images. Masking prevents the unit from being started manually or
pulled in by a dependency. To re-enable any of them:

```bash
systemctl unmask <service>
systemctl enable --now <service>
```

| Unit                        | Reason for disabling                                                        | Re-enable command                                  |
|-----------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| `cron.service`              | No scheduled jobs on the minimal image; cron keeps a resident process.      | `systemctl unmask cron.service`                    |
| `getty@tty2.service`        | A getty per VT costs ~1 MB each. Only `tty1` (the active console) is kept.  | `systemctl unmask getty@tty2.service`              |
| `getty@tty3.service`        | Same as `tty2`.                                                              | `systemctl unmask getty@tty3.service`              |
| `getty@tty4.service`        | Same as `tty2`.                                                              | `systemctl unmask getty@tty4.service`              |
| `getty@tty5.service`        | Same as `tty2`.                                                              | `systemctl unmask getty@tty5.service`              |
| `getty@tty6.service`        | Same as `tty2`.                                                              | `systemctl unmask getty@tty6.service`              |
| `apt-daily.timer`           | APT runs wake the system and run dpkg. The image is updated via bootc.      | `systemctl unmask apt-daily.timer`                 |
| `apt-daily-upgrade.timer`   | Same as `apt-daily.timer` (upgrade path).                                   | `systemctl unmask apt-daily-upgrade.timer`         |
| `apt-daily.service`         | Backing service unit for the timer above.                                  | `systemctl unmask apt-daily.service`               |
| `apt-daily-upgrade.service` | Backing service unit for the upgrade timer.                                | `systemctl unmask apt-daily-upgrade.service`       |
| `rsyslog.service`           | No syslog daemon installed. Masked to prevent a downstream layer from       | `systemctl unmask rsyslog.service`                |
|                             | pulling it in via a dependency. journald covers kernel + userspace logs.   |                                                    |
| `man-db.timer`              | No man pages installed; the whatis rebuild is pure overhead.               | `systemctl unmask man-db.timer`                    |
| `man-db.service`            | Backing service for the timer above.                                       | `systemctl unmask man-db.service`                  |
| `console-setup.service`     | Console font/keymap setup. Not needed on a headless image.                | `systemctl unmask console-setup.service`           |
| `keyboard-setup.service`    | Keyboard layout setup. Not needed on a headless image.                    | `systemctl unmask keyboard-setup.service`          |
| `e2scrub_all.timer`        | ext4 periodic check. bootc/composefs already covers integrity.            | `systemctl unmask e2scrub_all.timer`               |
| `e2scrub_all.service`      | Backing service for the timer above.                                       | `systemctl unmask e2scrub_all.service`             |
| `fstrim.timer`             | Periodic SSD TRIM. Spawns a process weekly. Unmask on SSDs.                | `systemctl unmask fstrim.timer`                    |
| `fstrim.service`           | Backing service for the timer above.                                       | `systemctl unmask fstrim.service`                  |
| `logrotate.timer`          | No persistent logs (`journald Storage=none`) and no `/var/log/*.log`.      | `systemctl unmask logrotate.timer`                 |
| `logrotate.service`        | Backing service for the timer above.                                       | `systemctl unmask logrotate.service`               |

## Kernel Configuration

Both minimal images ship a kernel config fragment in `kernel/`:

- `kernel/config-minimal-x86_64` — options that differ from the x86_64 defconfig.
- `kernel/config-minimal-arm64` — options that differ from the arm64 defconfig.

These files are **not** a full `.config`. They are meant to be merged into
the Debian default config with:

```bash
# In a kernel source tree matching the installed version
cp /boot/config-$(uname -r) .config
scripts/kconfig/merge_config.sh -m .config kernel/config-minimal-x86_64
make olddefconfig
```

### What is enabled

#### x86_64

- **Block storage (built-in):** `CONFIG_BLK_DEV_NVME`, `CONFIG_SATA_AHCI`,
  `CONFIG_VIRTIO_BLK`, `CONFIG_VIRTIO_PCI` — so the initramfs can find the
  rootfs without loading a module.
- **Network (modules):** `CONFIG_E1000`, `CONFIG_E1000E`, `CONFIG_VIRTIO_NET`,
  `CONFIG_IGB`, `CONFIG_R8169` — modules so they only load when the
  corresponding hardware is present.
- **Console (built-in):** `CONFIG_SERIAL_8250`, `CONFIG_SERIAL_8250_CONSOLE`
  — the kernel must be able to emit to the serial console before any module
  load.
- **Filesystems (built-in):** `CONFIG_EXT4_FS`, `CONFIG_XFS_FS`,
  `CONFIG_BTRFS_FS`, `CONFIG_TMPFS` — for the root filesystem types
  bootc/ostree may use.
- **USB host controllers (modules):** `CONFIG_USB_XHCI_HCD`,
  `CONFIG_USB_EHCI_HCD` — kept as modules for an emergency USB keyboard.

#### arm64

- **SoC platforms (built-in):** `CONFIG_ARCH_BCM2835`, `BCM2711`, `BCM2712`
  (Raspberry Pi 3/4/5), `CONFIG_ARCH_ROCKCHIP`, `CONFIG_ARCH_SUNXI`,
  `CONFIG_ARCH_MESON` — one kernel for all supported SBCs.
- **Serial (built-in):** `CONFIG_SERIAL_8250`, `CONFIG_SERIAL_AMBA_PL011`
  — covers the UARTs used by all supported SoCs.
- **MMC/SD (built-in):** `CONFIG_MMC_SDHCI`, `CONFIG_MMC_SDHCI_PLTFM`,
  `CONFIG_MMC_BCM2835` — most SBCs boot from SD or eMMC.
- **Ethernet (built-in):** `CONFIG_BCMGENET` (Raspberry Pi),
  `CONFIG_DWMAC_DWC_QOS_ETH`, `CONFIG_DWMAC_GENERIC`, `CONFIG_STMMAC_ETH`
  (Rockchip, Amlogic, Allwinner), `CONFIG_MESON_GXL_PHY` (Amlogic PHY).
- **USB (built-in):** `CONFIG_USB_DWC3`, `CONFIG_USB_XHCI_HCD`,
  `CONFIG_USB_EHCI_HCD`, `CONFIG_USB_OHCI_HCD` — USB is the only emergency
  console input on most SBCs.
- **Filesystems (built-in):** `CONFIG_EXT4_FS`, `CONFIG_XFS_FS`,
  `CONFIG_BTRFS_FS`, `CONFIG_TMPFS` — for the root filesystem types
  bootc/ostree may use. XFS and BTRFS are included for parity with the
  x86_64 minimal config.
- **RTC (built-in):** `CONFIG_RTC_CLASS`, `CONFIG_RTC_DRV_PL031` (Rockchip,
  Amlogic), `CONFIG_RTC_DRV_SUN6I` (Allwinner), `CONFIG_RTC_DRV_MESON`
  (Amlogic) — so systemd-timesyncd has a fallback time.
- **Virtio (built-in):** `CONFIG_VIRTIO_PCI`, `CONFIG_VIRTIO_BLK`,
  `CONFIG_VIRTIO_NET` — for ARM64 VMs.

### What is disabled

On both architectures:

- `# CONFIG_SOUND is not set` — no audio hardware.
- `# CONFIG_DRM is not set` — no display on a headless minimal image.
- `# CONFIG_BT is not set` — no Bluetooth.
- `# CONFIG_WIRELESS is not set`, `# CONFIG_CFG80211 is not set`,
  `# CONFIG_MAC80211 is not set` — no WiFi.

On x86_64 additionally:

- `# CONFIG_USB_HID is not set` — no USB HID at runtime (console is serial
  or KVM). The USB host controller drivers are kept as modules so a USB
  keyboard can be plugged in for emergency access (the module will need to
  be re-enabled in the kernel config or added back by a downstream layer).
- `# CONFIG_INPUT_JOYSTICK is not set`, `# CONFIG_INPUT_TABLET is not set`.

### How to recompile the kernel

The minimal images by default use the stock Debian `linux-image-amd64` /
`linux-image-arm64` packages. The config fragments in `kernel/` are for
users who want to build a custom kernel matching the minimal targets.

Prerequisites:

```bash
sudo apt install build-essential libncurses-dev bison flex libssl-dev \
                 libelf-dev bc rsync
```

Build steps:

```bash
# 1. Get the kernel source matching the installed version
apt source linux-image-$(uname -r)
cd linux-*/

# 2. Start from the Debian config
cp /boot/config-$(uname -r) .config

# 3. Merge the minimal fragment
scripts/kconfig/merge_config.sh -m .config kernel/config-minimal-x86_64
# or:
scripts/kconfig/merge_config.sh -m .config kernel/config-minimal-arm64

# 3.1. Resolve any new symbols introduced by the fragment against the
#      current kernel source. merge_config.sh leaves the .config in a
#      "needs olddefconfig" state when the fragment toggles options that
#      pull in new CONFIG symbols. Skipping this step produces a config
#      that does not match the source tree and silently drops options.
make olddefconfig

# 4. Tweak anything else interactively
make menuconfig

# 5. Build the kernel and modules
make -j"$(nproc)" bindeb-pkg

# 6. Install the resulting .deb files
sudo dpkg -i ../linux-image-*.deb ../linux-headers-*.deb
```

To integrate the custom kernel into a bootc image, install the `.deb`
files in a downstream `Containerfile`:

```dockerfile
FROM ghcr.io/daemoncores/debian-bootc-minimal:x86_64
COPY linux-image-*.deb /tmp/
RUN dpkg -i /tmp/linux-image-*.deb && rm /tmp/*.deb
```

## Memory Reduction Techniques

The table below lists every technique applied to reach the < 10 MB RAM
idle target, with an approximate saving per technique. Savings are
measured relative to the main `debian-bootc` image on the same hardware
and are approximate (they vary with kernel version and workload).

| Technique                                       | Approx. saving | Where applied                              |
|-------------------------------------------------|----------------|--------------------------------------------|
| `journald Storage=none`                         | 8–15 MB        | `Containerfile.minimal.*` Phase 5          |
| Kernel cmdline `quiet`                           | < 1 MB         | `Containerfile.minimal.*` Phase 6          |
| Kernel cmdline `init_on_alloc=0`                | 1–3 % of alloc throughput | `Containerfile.minimal.*` Phase 6 |
| Masking `cron.service`                          | ~1 MB          | `Containerfile.minimal.*` Phase 7          |
| Masking `getty@tty2..tty6` (5 gettys)            | ~5 MB          | `Containerfile.minimal.*` Phase 7          |
| Masking `apt-daily*`                             | < 1 MB idle    | `Containerfile.minimal.*` Phase 7          |
| Masking `man-db.timer`                          | < 1 MB idle    | `Containerfile.minimal.*` Phase 7          |
| Masking `console-setup` + `keyboard-setup`     | < 1 MB         | `Containerfile.minimal.*` Phase 7          |
| Masking `e2scrub_all` + `fstrim` + `logrotate` | < 1 MB idle    | `Containerfile.minimal.*` Phase 7          |
| Omitting `openssh-server`                       | ~3 MB          | Phase 3 package list                       |
| Omitting `podman`                               | ~10 MB at idle | Phase 3 package list                       |
| Omitting `man-db`, `manpages`, `groff-base`    | ~2 MB          | Phase 3 package list                       |
| Omitting `ifupdown2` (using `systemd-networkd`) | ~1 MB          | Phase 3 package list                       |
| Omitting `linux-headers-*` + `dkms`            | ~30 MB disk (not RAM)   | Phase 3 package list                       |
| Omitting microcode packages                     | ~2 MB boot image        | Phase 3 package list                       |
| Kernel config: `SND`, `DRM`, `BT`, `WLAN` off  | 5–20 MB        | `kernel/config-minimal-*`                 |
| Kernel config: `USB_HID` off (x86_64)          | ~1 MB          | `kernel/config-minimal-x86_64`             |

The biggest single win is `journald Storage=none`, which removes the
largest always-on userspace memory consumer after systemd itself. The
biggest cumulative win comes from disabling the sound, DRM, Bluetooth and
WLAN subsystems in the kernel config — those subsystems allocate
structures at boot even when no hardware is present.

## How to Re-enable Features

All of the following assume you are writing a downstream `Containerfile`
`FROM` one of the minimal images. The minimal images never re-enable
features at runtime by themselves.

### SSH

```dockerfile
FROM ghcr.io/daemoncores/debian-bootc-minimal:x86_64
RUN apt update && apt install -y openssh-server \
    && systemctl enable ssh.service \
    && rm -rf /var/lib/apt/lists/*
```

(Adjust the service name to `ssh.service` on Trixie; older Debian used
`sshd.service`.)

### cron

```dockerfile
RUN apt update && apt install -y cron \
    && systemctl unmask cron.service \
    && systemctl enable cron.service
```

### man pages

```dockerfile
RUN apt update && apt install -y man-db manpages \
    && systemctl unmask man-db.timer
```

### Persistent logging (journald)

```dockerfile
RUN rm -f /etc/systemd/journald.conf.d/00-minimal.conf \
    && mkdir -p /var/log/journal
```

### Multiple TTYs

```dockerfile
RUN systemctl unmask getty@tty2.service getty@tty3.service \
                     getty@tty4.service getty@tty5.service getty@tty6.service \
    && systemctl enable getty@tty2.service getty@tty3.service \
                        getty@tty4.service getty@tty5.service getty@tty6.service
```

### WiFi (ARM64 only)

WiFi drivers are disabled in `kernel/config-minimal-arm64`. To re-enable
WiFi on a specific SBC you must either:

1. Use the stock Debian `linux-image-arm64` (which has WiFi enabled) by
   overriding the kernel in a downstream layer, **or**
2. Build a custom kernel from the minimal config with the wireless
   subsystem re-enabled:

```bash
scripts/kconfig/merge_config.sh -m .config kernel/config-minimal-arm64
# Re-enable wireless
echo 'CONFIG_WIRELESS=y' >> .config
echo 'CONFIG_CFG80211=y' >> .config
echo 'CONFIG_MAC80211=y' >> .config
# Add the specific driver for your board, e.g.:
echo 'CONFIG_BRCMFMAC=m' >> .config     # Raspberry Pi
# echo 'CONFIG_RTW88=m' >> .config     # some Rockchip boards
make olddefconfig
```

### Bluetooth (ARM64 only)

Same approach as WiFi: either use the stock Debian kernel or rebuild the
minimal kernel with `CONFIG_BT=y` and the appropriate driver.

## Build Instructions

### Build the x86_64 minimal image

```bash
podman build \
    -f Containerfile.minimal.x86_64 \
    -t debian-bootc-minimal:x86_64 .
```

### Build the arm64 minimal image (native, on an ARM64 host)

```bash
podman build \
    -f Containerfile.minimal.arm64 \
    -t debian-bootc-minimal:arm64 .
```

### Cross-build the arm64 image from an x86_64 host

```bash
podman build \
    --arch arm64 \
    -f Containerfile.minimal.arm64 \
    -t debian-bootc-minimal:arm64 .
```

> `podman` uses qemu user-mode emulation when `--arch` differs from the
> host. Builds are slower than native but produce a correct image.

### Build a custom-kernel variant

```bash
# 1. Build the custom kernel .deb (see "How to recompile the kernel")
make -j"$(nproc)" bindeb-pkg

# 2. Write a downstream Containerfile
cat > Containerfile.custom <<'EOF'
FROM localhost/debian-bootc-minimal:x86_64
COPY linux-image-*.deb /tmp/
RUN dpkg -i /tmp/linux-image-*.deb && rm -f /tmp/*.deb
EOF

# 3. Build
podman build -f Containerfile.custom -t debian-bootc-minimal:custom .
```

### Push to a registry

```bash
podman push debian-bootc-minimal:x86_64 \
    ghcr.io/youruser/debian-bootc-minimal:x86_64
podman push debian-bootc-minimal:arm64 \
    ghcr.io/youruser/debian-bootc-minimal:arm64
```

### Deploy to a host

```bash
# On the target host, install via bootc
sudo bootc switch ghcr.io/youruser/debian-bootc-minimal:x86_64
```

## Known Limitations

- **No SSH server by default.** Access is via the serial console or the
  `bootc` recovery shell. Add `openssh-server` in a downstream layer.
- **Single TTY only.** `tty1` is the only active virtual console; `tty2`
  through `tty6` are masked. Unmask them if you need multiple consoles.
- **No persistent logging.** `journald Storage=none` drops log lines after
  they are forwarded. There is no `/var/log/journal`. To keep logs across
  reboots, remove `/etc/systemd/journald.conf.d/00-minimal.conf` in a
  downstream layer.
- **No man pages.** `man-db`, `manpages`, and `groff-base` are not
  installed. Re-add them in a downstream layer if needed.
- **No `bash-completion`, `nano`, `less`.** The minimal image ships only
  the busybox-style essentials. Downstream layers can add any editor.
- **ARM64: no WiFi.** The wireless subsystem is disabled in the kernel
  config fragment. Use the stock Debian kernel or rebuild the minimal
  kernel with WiFi re-enabled for a specific SBC.
- **ARM64: no Bluetooth.** Same as WiFi.
- **ARM64: no GPU.** DRM is disabled in the kernel config; the console is
  serial or framebuffer-only. Re-enable DRM in the kernel config for a
  desktop SBC use case.
- **No microcode updates (x86_64).** `intel-microcode` and `amd64-microcode`
  are not installed. Re-add them in a downstream layer for bare-metal
  deployments that need CPU errata patches.
- **No Secure Boot MOK support (x86_64).** The minimal x86_64 image
  installs the **unsigned** `grub-efi-amd64` package (the Fedora rhboot
  fork with BLS modules). It does **not** install
  `grub-efi-amd64-signed` or the `shim-signed` MOK chain. As a result the
  image will not boot on a host with Secure Boot enforced in firmware
  unless a downstream layer adds `grub-efi-amd64-signed` + `shim-signed`
  and re-runs `bootc finalize`. The main `debian-bootc` image does install
  the signed packages; the minimal image trades Secure Boot support for a
  smaller boot stack.
- **No `firstboot-user-setup`.** The interactive first-boot wizard is
  omitted. The minimal image is intended for headless deployments where
  the user is configured by a downstream layer or a configuration
  management tool.

## Related Documents

- [`README.md`](../README.md) — Project overview, quick start, technical stack.
- [`docs/architecture.md`](architecture.md) — Full architecture of the
  main `debian-bootc` image (the minimal images share the bootc/ostree/
  composefs/dracut stack documented there).
- [`docs/justifications.md`](justifications.md) — Honest justifications for
  the design choices of the main image; the minimal images inherit most of
  them (dracut over initramfs-tools, trixie base, etc.).
- [`Containerfile.minimal.x86_64`](../Containerfile.minimal.x86_64) — x86_64
  image definition, line-by-line commented.
- [`Containerfile.minimal.arm64`](../Containerfile.minimal.arm64) — ARM64
  image definition, line-by-line commented.
- [`kernel/config-minimal-x86_64`](../kernel/config-minimal-x86_64) — x86_64
  kernel config fragment.
- [`kernel/config-minimal-arm64`](../kernel/config-minimal-arm64) — ARM64
  kernel config fragment.