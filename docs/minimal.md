# Minimal image

`Containerfile.minimal` defines a reduced Debian 13 bootc image for hosts that need a small system layer rather than the interactive tooling provided by the full image.

It is a separate image contract. It should not be described as the full image with a few packages removed.

## Included system

The minimal image installs:

- the project-provided kernel package selected by `KERNEL_VARIANT` and `ARCH`;
- bootc and dracut;
- the architecture-specific boot package;
- architecture/device kernel-module packages;
- `iproute2`, systemd-timesyncd, and CA certificates.

The image retains the OSTree filesystem layout used by the full image.

## Deliberate omissions

The minimal image does not install the full image's ifupdown2, administration manuals, editor, shell-completion set, broad firmware set, or general troubleshooting utilities.

`openssh-server` is installed to support the CI SSH test harness (QEMU boot tests connect over SSH). Deployments that do not need an SSH server should remove it in a downstream image.

Operational consequences:

- use the local console or a downstream image for interactive access without the SSH server;
- do not expect Podman to be available on the deployed host;
- use systemd-networkd rather than `/etc/network/interfaces`;
- diagnostics must fit the smaller installed toolset;
- persistent journald storage is disabled.

## Networking

The image enables `systemd-networkd.service`, `systemd-networkd.socket`, and systemd-timesyncd. The default `.network` file enables DHCP for interfaces matching `en*` or `eth*`.

Boards whose interface names do not match those patterns need a downstream network definition.

## Services and logging

Journald is configured with `Storage=none`. The following background or maintenance units are masked by the Containerfile:

- cron;
- getty instances on tty2 through tty6;
- APT daily and upgrade timers;
- rsyslog;
- man-db;
- console and keyboard setup;
- filesystem scrub and trim timers;
- logrotate.

Unmask only the services needed by the deployed role.

## Build arguments

| Argument | Default | Meaning |
| --- | --- | --- |
| `ARCH` | `amd64` | Debian architecture used in kernel and module package names. |
| `BOOT_PKG` | `grub-efi-amd64-signed` | Architecture-specific boot package. |
| `FIRMWARE_PKGS` | empty | Additional firmware packages. |
| `KERNEL_CMDLINE_SERIAL` | empty | Extra serial-console kernel arguments. |
| `KERNEL_VARIANT` | `minimal` | Selects `linux-image-<variant>-<arch>`. |
| `AUTOUPDATE` | `1` | Writes the bootc automatic-update mode into the image. |
| `PRODUCT_NAME` | empty | Display name consumed by the boot finalization tooling. |

The expected kernel and module packages must already exist in the project's APT repository.

## Local builds

amd64 example:

```bash
podman build --format docker \
  --build-arg ARCH=amd64 \
  --build-arg BOOT_PKG=grub-efi-amd64-signed \
  --build-arg KERNEL_VARIANT=minimal \
  --build-arg AUTOUPDATE=1 \
  -f Containerfile.minimal \
  -t debian-bootc:minimal-amd64 .
```

arm64 example on a native arm64 host:

```bash
podman build --format docker \
  --build-arg ARCH=arm64 \
  --build-arg "BOOT_PKG=grub-efi-arm64-signed" \
  --build-arg BOOT_PROFILE=generic \
  --build-arg FIRMWARE_PKGS="firmware-linux-free firmware-misc-nonfree" \
  --build-arg KERNEL_CMDLINE_SERIAL="console=ttyAMA0,115200 console=ttyS0,115200 console=ttyAML0,115200" \
  --build-arg KERNEL_VARIANT=minimal \
  --build-arg AUTOUPDATE=1 \
  -f Containerfile.minimal \
  -t debian-bootc:minimal-arm64 .
```

Use `AUTOUPDATE=0` for a lock variant.

## Kernel and auto-update

- The kernel is not built by the Containerfile: `linux-image-${KERNEL_VARIANT}-${ARCH}` is installed from the project APT repository and resolves to the custom `daemoncores-kernel-<kver>` package (published as `linux-image-common_*.deb`) through its `Provides: linux-image-minimal-<arch>`. On arm64 a second kernel with 16 KB pages is published as `linux-image-common-16k_*.deb` and provides `linux-image-minimal-16k-arm64`; the `-16k` image installs it through `KERNEL_SUFFIX=-16k` (see [kernel-patches.md](kernel-patches.md)). The package Conflicts with and Replaces the Debian `linux-image-<kver>` it overlaps, following the ostree package model. Until the kernel build has published its first `.deb`, the install fails because the package exists in no repository (expected).
- The kernel config fragments and per-device module lists live in `workflows/bootc-debs-builder/kernel/`; `KERNEL_VARIANT=minimal` is the default and installs the kernel built from them. The standard image installs the same kernel and the same module packages.
- Memory: the minimal kernel keeps every driver (as modules, loaded by udev only when the device exists) and drops kernel machinery instead: BTF, the function tracer, profiling hooks, scheduler statistics, kexec and crash dump, the embedded config, and on x86_64 `NR_CPUS` 8192 → 512 [src: file: workflows/bootc-debs-builder/kernel/config:331-359] [src: file: workflows/bootc-debs-builder/kernel/modules/x86_64:123-127]. The 10-15 MB idle target is a direction, not a measured result: the options are applied but no boot has been measured, and the distribution userspace (systemd, dbus, sshd) already uses more than that on its own.
- `AUTOUPDATE=1` writes `1` to `/usr/lib/bootc/autoupdate`; `AUTOUPDATE=0` writes `0`, which bootc reads as disabled (the file's presence alone is not enough). The lock variant uses it to avoid background upgrades on minimal RAM.

## Architecture boundary

On amd64 the boot package is the project's signed GRUB package. On arm64 the current minimal definition expects U-Boot tooling and installs the generic ARM module set plus Raspberry Pi 3/4/5 and RK3588 module overlays.

A generic arm64 image does not make every board directly bootable. Board firmware, U-Boot configuration, DTB selection, storage layout, and console configuration remain platform responsibilities.

## Embedded profile and adding a board or chip

The `embedded` boot profile (`LABEL org.daemoncores.boot-profile`) is for arm64
boards whose firmware loads U-Boot; Android phones are out of scope (separate
repository). It changes only the boot stack: the kernel is the same single
kernel and the per-board hardware support is a module package.

To add a board or chip:

1. Create `workflows/bootc-debs-builder/kernel/modules/<chip>` with only the
   options specific to that chip (SoC platform, controllers, drivers). Options
   shared by all ARM devices belong in `kernel/modules/arm`, and options shared by
   every device in `kernel/config`.
2. Add `<chip>` to the `variants` of `linux-modules-arm-device` in
   `workflows/bootc-debs-builder/packages.yml`, with a `deps` on
   `linux-modules-arm` (4 KB kernel) or, plus `env: {KERNEL_SUFFIX: "-16k"}`,
   on `linux-modules-arm-16k` (16 KB kernel), as the existing chips do. The CI expands one build job per
   variant and passes the name as `DEVICE`; the build script is shared.
3. Add the chip to the `ARM_DEVICES` default of `Containerfile.minimal` and
   `Containerfile` (4 KB kernel) or to the 16 KB list in
   `DaemonCores-CI/.github/workflows/bootc-build.yml`.
4. Check the symbols against the current kernel with
   `check_kconfig.py --tree <kernel source> kernel/config kernel/modules/arm kernel/modules/<chip>`.
5. A device patch is only added if mainline lacks the driver; it follows the
   module-or-kernel rule in [kernel-patches.md](kernel-patches.md).

Firmware, U-Boot configuration, DTB selection and storage layout stay the
responsibility of the platform, as stated above.

## Validation checklist

Before publishing a minimal variant, verify at least:

- the correct architecture-specific kernel and modules are installed;
- the initramfs contains the bootc and OSTree integration;
- the target firmware can load the selected kernel and DTB;
- the default interface matches the networkd rule or has an override;
- the intended `AUTOUPDATE` value is present;
- recovery remains possible without SSH and without persistent logs.
