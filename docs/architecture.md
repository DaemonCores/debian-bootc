# debian-bootc Architecture

**Atomic / bootc (OSTree) image based on Debian 13 (Trixie)**

This document describes the architecture of debian-bootc: its layered composition, the CI/CD build pipeline, the runtime first-boot flow, and key design decisions.

---

## 1. Project Overview

debian-bootc is a bootc-compliant OSTree image that delivers Debian 13 (Trixie) as an atomic, rollback-capable operating system. It is the **base layer** for projects like DaemonCores-VE, providing the full bootc/OSTree infrastructure that other projects can extend.

The project follows the **bootc model**: the entire OS is built in a standard container pipeline (`podman build`), pushed to a container registry (GHCR), and applied atomically to the host using ostree as the on-disk storage engine. Updates are transactional and fully rollback-capable from the bootloader.

---

## 2. Layered Architecture

debian-bootc is designed as a **base layer** that other projects can build upon:

| Layer | Source | Responsibility |
|---|---|---|
| **debian-bootc** | This repository | bootc, ostree, composefs, bootupd, GRUB (Fedora rhboot fork), dracut, firstboot-user-setup, ifupdown2 (repacked), systemd-timesyncd (repacked), Secure Boot signing, APT repository |
| **Downstream layers** | Other repositories (e.g., DaemonCores-VE) | Hypervisor, application, or custom tooling built `FROM ghcr.io/daemoncores/debian-bootc:latest` |

### What the base layer provides

- **bootc / ostree** — atomic OS management, content-addressed filesystem, rollback
- **composefs** — fs-verity integrity protection for deployed OS trees
- **bootupd** — EFI System Partition management independent of ostree
- **GRUB** — Fedora rhboot fork with BLS (`blscfg`, `blsuki`) support
- **dracut** — initramfs with `bootc`, `lvm`, and `ostree` modules
- **firstboot-user-setup** — TUI wizard for hostname, locale, user accounts, root password, sudo, SSH policy
- **ifupdown2** — repacked with systemd unit ordering patches for bootc compatibility
- **systemd-timesyncd** — repacked with `After=network-online.target` drop-in
- **Secure Boot** — MOK-enrolled GRUB signed with the debian-bootc signing key
- **APT repository** — signed APT repo on GitHub Pages for all custom packages

---

## 3. Build Pipeline

The CI/CD pipeline is orchestrated by `.github/workflows/pipeline.yml` and consists of **three sequential stages**:

```
┌─────────────────────┐     ┌───────────────┐     ┌───────────────────┐
│  bootc-debs-builder │───▶│  bootc-build  │───▶│       iso         │
│                     │     │               │     │                   │
│  Compile from src:  │     │  Build OCI    │     │  Download Fedora  │
│  - libcomposefs     │     │  image from   │     │  netinstall ISO   │
│  - libostree        │     │  Containerfile│     │  Inject branding  │
│  - bootupd          │     │               │     │  Render kickstart │
│  - grub-efi-signed  │     │  Push to      │     │  Build online ISO │
│  - bootc            │     │  GHCR         │     │  Build offline ISO│
│  - firstboot-setup  │     │               │     │                   │
│  - ifupdown2 repack │     │  Sign with    │     │                   │
│  - timesyncd repack │     │  cosign       │     │  Upload to        │
│                     │     │               │     │  GitHub Releases  │
│  Publish APT repo   │     │  Smoke test:  │     │                   │
│  to GitHub Pages    │     │  bootc lint   │     │                   │
└─────────────────────┘     └───────────────┘     └───────────────────┘
```

### Stage 1: `bootc-debs-builder.yml`

Runs inside a `debian:trixie` container. Its responsibilities:

1. **Install build dependencies** — compilers, Rust toolchain, Meson, etc.
2. **Build custom `.deb` packages** from source:
   - `libcomposefs`, `libostree`, `bootupd`, `grub-efi-signed`, `bootc`, `firstboot-user-setup`
   - Repacked `ifupdown2` with bootc-specific patches
   - Repacked `systemd-timesyncd` with `After=network-online.target` drop-in
3. **Publish the APT repository** to GitHub Pages using `morph027/apt-repo-action`

The resulting `.deb` artifacts are uploaded as workflow artifacts and consumed by the base image build.

### Stage 2: `bootc-build.yml`

Runs on `ubuntu-latest`. Its responsibilities:

1. **Free disk space** — remove unused toolchains to make room for the image build
2. **Log in to GHCR** — authenticate both Podman (for build/push) and Docker (for cosign signing)
3. **Build the OCI image** using `podman build` from the `Containerfile`
   - On scheduled monthly builds: `--no-cache` is passed, and a `monthly-YYYYMMDD` tag is added
4. **Check runtime dependencies** — verify `bootc` and `libostree` are present and linked
5. **Smoke test** — run `bootc container lint` inside the built image
6. **Push to GHCR** — push `:latest`, `:short-sha`, and optionally `:monthly-YYYYMMDD`
7. **Sign the image** with cosign using keyless Sigstore signing via GitHub Actions OIDC

### Stage 3: `iso.yml`

Runs inside an `almalinux:10` **privileged** container. Its responsibilities:

1. **Install ISO build tools** — `xorriso`, `squashfs-tools`, `lorax`, `mkksiso`, `ImageMagick`, `podman`, `gh-cli`, `cosign`
2. **Download Fedora Server netinstall ISO** — the Anaconda-based installer base
3. **Customize the ISO** — run `scripts/inject-iso.sh` to inject branding (sidebar, topbar, header, product name) and Anaconda module configuration into the squashfs
4. **Verify the container image signature** using `cosign verify` before embedding
5. **Pull and save the OCI image** — for the offline ISO, the image is saved as an OCI archive and embedded in the ISO
6. **Render Kickstart templates** — two templates (`iso-online-config.ks.tpl` and `iso-offline-config.ks.tpl`) are rendered to `/tmp/`
7. **Build online and offline ISOs** using `mkksiso`:
   - **Online ISO** — pulls the image from GHCR at install time
   - **Offline ISO** — embeds the OCI archive; no network required
8. **Patch GRUB configs** — replace Fedora branding with project branding in both EFI and BIOS GRUB configs
9. **Re-implant ISO MD5 checksum** — so media verification still works
10. **Upload ISOs to GitHub Releases** — attached to the `install-iso` release

### Pipeline orchestration

The `pipeline.yml` workflow ties the three stages together with `workflow_call`. Each stage can be toggled independently via `workflow_dispatch` inputs, allowing partial rebuilds (e.g., rebuild only the ISO without recompiling all `.deb` packages).

The pipeline runs automatically on the first of every month (`cron: '0 4 1 * *'`), rebuilding everything from scratch with `--no-cache` to incorporate upstream security updates.

---

## 4. Image Composition (Containerfile)

The `Containerfile` defines the debian-bootc base image. It is built `FROM debian:trixie`.

### Build phases

1. **Environment setup**
   - `STOPSIGNAL SIGRTMIN+3` — required for systemd-in-container compatibility
   - `DEBIAN_FRONTEND=noninteractive` — suppress interactive debconf prompts
   - `SHELL ["/bin/bash", "-euo", "pipefail", "-c"]` — fail fast on any error
   - `BOOTC_GPG_SHA256` — SHA-256 checksum of the APT repo signing key, verified at build time

2. **SSL and package prerequisites**
   - Install `ca-certificates`, `openssl`, `git`, `curl`, `wget`
   - Rewrite Debian APT sources from `http://` to `https://`
   - Remove the known-broken NetLock Arany certificate

3. **APT repository trust**
   - Download the debian-bootc APT signing key to `/usr/share/keyrings/debian-bootc-keyring.gpg`
   - Verify the key against the hardcoded SHA-256 before trusting it

4. **Base package installation**
   - Install the Debian kernel (`linux-image-amd64`, `linux-headers-amd64`)
   - Install firmware packages (`firmware-linux-free`, `firmware-linux`, `firmware-misc-nonfree`, `intel-microcode`, `amd64-microcode`)
   - Install `bootc` and `firstboot-user-setup` from the custom APT repository
   - Install standard utilities: `sudo`, `locales`, `openssh-server`, `nano`, `man-db`, `less`, etc.
   - Install networking: `ifupdown2`, `isc-dhcp-client`, `wpasupplicant`, `iproute2`
   - Install `systemd-timesyncd` (repacked)

5. **Filesystem migration for ostree**
   - Create `/var/home`, `/var/roothome`, `/var/mnt`, `/var/srv`, `/var/opt`
   - Copy `/usr/lib/locale` contents to `/var/usr/lib/locale`
   - Remove `/home`, `/root`, `/mnt`, `/srv`, `/opt` and replace with symlinks into `/var`
   - Symlink `/ostree` to `/sysroot/ostree`
   - Symlink `/usr/lib/locale` to `/var/lib/locale`

6. **Health check**
   - `HEALTHCHECK NONE` — bootc images are updated in-place via ostree; no runtime healthcheck applies

---

## 5. First-Boot Flow

When the image boots for the first time (whether from ISO installation or a direct `bootc switch`), the following sequence runs:

```
┌─────────────────────────────┐
│  System boots (GRUB + BLS)  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  dracut initramfs           │
│  (bootc, lvm, ostree modules)│
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  ostree deploys rootfs       │
│  (composefs + fs-verity)     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  systemd multi-user.target   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  firstboot-user-setup        │
│  (TUI wizard on tty1)        │
│  - Hostname                  │
│  - Locale / keyboard         │
│  - Primary user account        │
│  - Root password               │
│  - Sudo privileges             │
│  - SSH root login policy       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  ifupdown2-autoconf           │
│  (DHCP on first boot)         │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  networking fully online     │
└─────────────────────────────┘
```

### firstboot-user-setup

A TUI wizard modelled after the Raspberry Pi OS `userconfig` service. Runs as `ExecStartPre` on `getty@tty1.service` before the login prompt appears. It guides through:

- Hostname (validated against RFC 952)
- System locale (`dpkg-reconfigure locales`)
- Keyboard layout (`dpkg-reconfigure keyboard-configuration`)
- Primary user account — username, full name, password (8 characters minimum)
- Root password
- Sudo privileges
- SSH root login policy

Writes `/var/lib/firstboot-user-setup.done` on completion to prevent re-execution. The temporary root password (`BootcDebug@0`) is replaced by the user-supplied password, and `chage -d 0` forces a change on next login.

### ifupdown2-autoconf

An `ifupdown2-autoconf` helper performs DHCP autoconfiguration on first boot if the interfaces file has not yet been customised. This ensures the system has network connectivity before the user manually configures interfaces.

---

## 6. Networking

### Network manager

debian-bootc uses **ifupdown2** (repacked from Proxmox sources with bootc-specific patches) instead of `systemd-networkd`. The rationale is documented in [`docs/justifications.md`](justifications.md).

### Systemd unit ordering

The `ifupdown2-pre.service` is ordered `After=ostree-remount.service` to ensure the ostree read-only root is mounted before networking attempts to start. Without this ordering, `ifupdown2` can race against ostree remount and fail to bring up interfaces.

### Default configuration

The base image does not ship a pre-configured `/etc/network/interfaces` file. Downstream layers (e.g., DaemonCores-VE) are expected to provide their own network configuration. The `ifupdown2-autoconf` helper provides temporary DHCP on first boot to ensure basic connectivity.

---

## 7. Storage

### OSTree

OSTree is the filesystem layer underneath bootc. It stores OS trees in a content-addressed object store modelled after Git, deploys them via hard links for storage efficiency, and makes every deployment atomic. It manages `/usr`, `/etc`, and `/boot` while delegating `/var` and `/home` to normal mutable storage.

This build is compiled from upstream sources with:
- **composefs support** enabled for filesystem integrity
- **dracut integration** — the `50ostree` dracut module and `ostree-system-generator` for initramfs and early boot integration
- **prepare-root** configured for read-only sysroot

### composefs

composefs provides integrity protection for ostree deployments using fs-verity. Every file in the deployed OS tree is verified against a cryptographic hash at read time, making it impossible to tamper with the system at rest without detection.

Enabled in `prepare-root.conf`:
```ini
[sysroot]
readonly=true

[composefs]
enabled=yes
```

### bootupd

bootupd manages the EFI System Partition independently of the ostree-managed root filesystem. In a bootc system the EFI binaries (shim, GRUB) live outside the ostree tree and cannot be updated through the normal container image update path. bootupd bridges this gap by tracking and updating EFI binaries as a separate managed component.

The `bootc-finalize` script (run at package install time inside the container build) sets up the bootupd metadata by calling `bootupctl backend generate-update-metadata`.

---

## 8. Secure Boot

### Chain of trust

```
UEFI firmware → shim-signed (Microsoft-signed) → grubx64.efi (debian-bootc-signed) → kernel
```

### Signing key

The `grub-efi-amd64-signed` package includes:

- A GRUB EFI binary signed with the debian-bootc Secure Boot signing key
- The signing certificate at `/usr/share/debian-bootc/sb_signing.crt`
- A `postinst` script that queues MOK enrollment automatically on package install

### MOK enrollment flow

1. **First boot after installation** — the firmware launches the blue MokManager screen
2. Select **Enroll MOK**
3. Select **Continue**
4. Select **Yes**
5. Enter the enrollment password when prompted
6. Select **Reboot**

The signing key is then enrolled permanently. All subsequent boots are fully verified end-to-end without any further action.

### Verification

```bash
mokutil --sb-state          # confirm Secure Boot is active
mokutil --list-enrolled     # confirm the debian-bootc key is present
```

---

## 9. Documentation Toolchain

| Component | Tool | Output |
|---|---|---|
| Inline docs | POSIX shell header blocks | Source code |
| Static docs | Markdown in `docs/` | GitHub web UI, wiki |
| Wiki sync | CI workflow (`docs-wiki-sync.yml`) | GitHub wiki |
| Reference extraction | `shdoc` (for shell scripts) | Markdown |

The `docs/reference/` directory is auto-generated by CI from inline header blocks and is **not committed** to the repository.

---

## 10. Related Documents

- [`README.md`](../README.md) — Project overview, quick start, technical stack
- [`docs/justifications.md`](justifications.md) — Honest justifications for controversial design choices
- [`Containerfile`](../Containerfile) — Image composition definition
