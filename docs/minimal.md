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

The minimal image does not install the full image's SSH server, Podman, ifupdown2, administration manuals, editor, shell-completion set, broad firmware set, or general troubleshooting utilities.

Operational consequences:

- use the local console or add SSH in a downstream image;
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
| `KERNEL_VARIANT` | `stock` | Selects `linux-image-<variant>-<arch>`. |
| `AUTOUPDATE` | `1` | Writes the bootc automatic-update mode into the image. |
| `PRODUCT_NAME` | empty | Display name consumed by the boot finalization tooling. |

The expected kernel and module packages must already exist in the project's APT repository.

## Local builds

amd64 example:

```bash
podman build --format docker \
  --build-arg ARCH=amd64 \
  --build-arg BOOT_PKG=grub-efi-amd64-signed \
  --build-arg KERNEL_VARIANT=stock \
  --build-arg AUTOUPDATE=1 \
  -f Containerfile.minimal \
  -t debian-bootc:minimal-amd64 .
```

arm64 example on a native arm64 host:

```bash
podman build --format docker \
  --build-arg ARCH=arm64 \
  --build-arg BOOT_PKG=u-boot-tools \
  --build-arg FIRMWARE_PKGS="firmware-linux-free firmware-misc-nonfree" \
  --build-arg KERNEL_CMDLINE_SERIAL="console=ttyAMA0,115200 console=ttyS0,115200 console=ttyAML0,115200" \
  --build-arg KERNEL_VARIANT=stock \
  --build-arg AUTOUPDATE=1 \
  -f Containerfile.minimal \
  -t debian-bootc:minimal-arm64 .
```

Use `AUTOUPDATE=0` for a lock variant.

## Architecture boundary

On amd64 the boot package is the project's signed GRUB package. On arm64 the current minimal definition expects U-Boot tooling and installs the generic ARM module set plus Raspberry Pi 3/4/5 and RK3588 module overlays.

A generic arm64 image does not make every board directly bootable. Board firmware, U-Boot configuration, DTB selection, storage layout, and console configuration remain platform responsibilities.

## Validation checklist

Before publishing a minimal variant, verify at least:

- the correct architecture-specific kernel and modules are installed;
- the initramfs contains the bootc and OSTree integration;
- the target firmware can load the selected kernel and DTB;
- the default interface matches the networkd rule or has an override;
- the intended `AUTOUPDATE` value is present;
- recovery remains possible without SSH and without persistent logs.
