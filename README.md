# debian-bootc

**The first fully integrated, production-ready Debian 13 (Trixie) bootc image.**

Every previous attempt to run bootc on Debian either stopped at a proof-of-concept
stage or was quietly abandoned. This repository delivers a complete, CI-tested,
automatically maintained image ready for production deployment — no manual assembly,
no missing pieces.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Is this repository abandoned?](#is-this-repository-abandoned)
- [Technical stack](#technical-stack)
- [CI/CD pipeline](#cicd-pipeline)
- [APT repository](#apt-repository)
- [Secure Boot](#secure-boot)
- [Required secrets](#required-secrets)
- [Quick start](#quick-start)
- [License](#license)

---

## Why this exists

The bootc ecosystem — bootc, ostree, composefs, bootupd — was developed primarily
for Fedora and RHEL. Debian ships none of these packages, and there is no official
plan to include them in the foreseeable future. Every previous community effort
produced either a partial proof-of-concept or an abandoned repository.

This project solves the problem end-to-end:

1. **Builds all missing packages from source** and publishes them in a signed APT
   repository on GitHub Pages, making them installable like any other Debian package.
2. **Builds a bootc-compliant OCI container image** based on `debian:trixie`, pushed
   to GHCR and signed with cosign via Sigstore keyless signing.
3. **Builds Anaconda-based installer ISOs** — both online (pulls from GHCR at install
   time) and offline (OCI image embedded in the ISO) — for bare-metal and VM
   deployments with a single boot sequence.

---

## Is this repository abandoned?

**No.** The repository may appear inactive between Debian releases by design.

### Monthly automated rebuilds

The CI pipeline runs automatically on the first of every month and rebuilds the full
distribution image from scratch with `--no-cache`, incorporating all upstream Debian
security updates as they land in the `trixie` and `trixie-security` repositories.
All custom `.deb` packages (ostree, composefs, bootupd, bootc, GRUB) are rebuilt
from source on the same schedule.

### Audited packages

The custom packages have been audited to confirm they introduce no network-exposed
attack surface:

- None of them listens on a socket, modifies firewall rules, or establishes outbound
  connections at install time or service startup.
- The only modified packages that could be considered sensitive — **ifupdown2** and
  **systemd-timesyncd** — are repacked from audited Debian and Proxmox sources with
  minimal, targeted, fully documented patches. Their changes are limited to systemd
  unit ordering and a single DHCP autoconfiguration helper.
- All other custom packages are compiled from upstream sources that are actively
  maintained and tracked for security by their respective projects (ostree, composefs,
  bootc, bootupd).

### Release lifecycle

The current target is **Debian 13 Trixie**. A new release cycle will begin when
Debian 14 is published. Between now and then, the only expected changes are:

- Monthly automated security rebuilds (triggered by CI schedule).
- Version bumps for upstream components (bootc, ostree, bootupd, composefs, GRUB)
  when new releases are available.

The absence of frequent commits is a sign of stability, not abandonment.

---

## Technical stack

### bootc

[bootc](https://github.com/bootc-dev/bootc) treats the entire operating system as
an OCI container image. Rather than managing packages individually on a running
system, the OS is built in a standard container pipeline, pushed to a registry, and
applied atomically to the host using ostree as the on-disk storage engine. Updates
are transactional and fully rollback-capable from the bootloader.

**Why:** Brings GitOps-style OS management — the same model that powers Fedora
CoreOS and RHEL Image Mode — to Debian, with the stability and package ecosystem
that Debian provides.

### ostree

[OSTree](https://ostreedev.github.io/ostree/) is the filesystem layer underneath
bootc. It stores OS trees in a content-addressed object store modelled after Git,
deploys them via hard links for storage efficiency, and makes every deployment
atomic. It manages `/usr`, `/etc`, and `/boot` while delegating `/var` and `/home`
to normal mutable storage — which is why `/home`, `/root`, `/srv`, `/mnt`, and
`/opt` are symlinked into `/var` in this image.

This build is compiled from upstream sources with:
- **composefs support** enabled for filesystem integrity
- **dracut integration** — the `50ostree` dracut module and `ostree-system-generator`
  for initramfs and early boot integration
- **prepare-root** configured for read-only sysroot

### composefs

[composefs](https://github.com/composefs/composefs) provides integrity protection for
ostree deployments using
[fs-verity](https://www.kernel.org/doc/html/latest/filesystems/fsverity.html). Every
file in the deployed OS tree is verified against a cryptographic hash at read time,
making it impossible to tamper with the system at rest without detection.

Enabled in `prepare-root.conf`:
```ini
[sysroot]
readonly=true

[composefs]
enabled=yes
```

### bootupd

[bootupd](https://github.com/coreos/bootupd) manages the EFI System Partition
independently of the ostree-managed root filesystem. In a bootc system the EFI
binaries (shim, GRUB) live outside the ostree tree and cannot be updated through
the normal container image update path. bootupd bridges this gap by tracking and
updating EFI binaries as a separate managed component.

The `bootc-finalize` script (run at package install time inside the container build)
sets up the bootupd metadata by calling `bootupctl backend generate-update-metadata`.

### GRUB — Fedora rhboot fork

The standard Debian `grub-efi-amd64-signed` package does not include the `blscfg`
and `blsuki` modules required by ostree and bootc for
[BLS](https://uapi-group.org/specifications/specs/boot_loader_specification/)
(Boot Loader Specification) kernel entry management. This repository compiles GRUB
from the [Fedora rhboot/grub2](https://github.com/rhboot/grub2) fork at a pinned
commit, producing a `grubx64.efi` with full BLS support.

### dracut

[dracut](https://github.com/dracut-ng/dracut-ng) generates the initramfs embedded in
the deployed image. It is configured with the `bootc`, `lvm`, and `ostree` modules,
`zstd` compression, and `hostonly=no` so the initramfs works on any hardware. The
initramfs is built inside the container during the `bootc` package post-install
hook (`bootc-finalize`), so the deployed image is fully self-contained.

### ifupdown2 (Proxmox repack)

ifupdown2 is sourced from the Proxmox repository. This image is designed to serve as
a foundation for a Proxmox-based bootc deployment, and ifupdown2 is the network
manager used by Proxmox. The package is repacked with two targeted patches:

- `ifupdown2-pre.service` is ordered `After=ostree-remount.service` to ensure the
  ostree read-only root is mounted before networking attempts to start.
- An `ifupdown2-autoconf` helper performs DHCP autoconfiguration on first boot if
  the interfaces file has not yet been customised.

### systemd-timesyncd (repack)

Repacked with a single drop-in that adds `After=network-online.target` and
`Wants=network-online.target` to `systemd-timesyncd.service`. Without this,
timesyncd attempts to reach NTP servers before the network interface is up in a
bootc environment, causing spurious service failures at boot.

### firstboot-user-setup

A TUI wizard modelled after the Raspberry Pi OS `userconfig` service. Runs on the
first boot before the login prompt and guides through:

- Hostname (validated against RFC 952)
- System locale (`dpkg-reconfigure locales`)
- Keyboard layout (`dpkg-reconfigure keyboard-configuration`)
- Primary user account — username, full name, password (8 chars minimum)
- Root password
- Sudo privileges
- SSH root login policy

Runs as `ExecStartPre` on `getty@tty1.service` and writes
`/var/lib/firstboot-user-setup.done` on completion to prevent re-execution.

### Anaconda + Kickstart

The installer ISOs are built from the Fedora Server netinstall ISO with Anaconda as
the installation engine. Two Kickstart templates are provided:

| ISO | Source | Use case |
|-----|--------|----------|
| `online` | Pulls `ghcr.io/<repo>:latest` from the registry at install time | Networked install, always latest image |
| `offline` | OCI archive embedded in the ISO | Air-gapped install, pinned image version |

Both templates configure LVM on XFS, delegate user setup to `firstboot-user-setup`,
and set a temporary root password that is replaced on first boot.

**Note on default root password:** The kickstart installer sets a temporary default
root password `BootcDebug@0`. This is a deliberate fallback: if the first-boot
user-setup wizard fails to run or is interrupted, the system remains accessible via
root login so you are not locked out of your own machine. The password is replaced
by the wizard on first successful boot, and the root account is forced to change
password via `chage -d 0`.

The ISO branding (sidebar, topbar, header, product name) and Anaconda module
configuration are injected into the squashfs installer environment by
`scripts/inject-iso.sh`.

### cosign / Sigstore

The container image is signed with [cosign](https://github.com/sigstore/cosign) via
keyless Sigstore signing using the GitHub Actions OIDC identity. The signature is
stored in the same GHCR namespace as the image.

Verify a pulled image:
```bash
cosign verify ghcr.io/DaemonCores/debian-bootc:latest \
  --certificate-identity-regexp \
    "https://github.com/DaemonCores/debian-bootc/.github/workflows/bootc-build.yml@refs/heads/main" \
  --certificate-oidc-issuer \
    "https://token.actions.githubusercontent.com"
```

---

## CI/CD pipeline

```
┌─────────────────────┐     ┌──────────────┐     ┌───────────────────┐
│  bootc-debs-builder │───▶│ bootc-build  │───▶│       iso         │
│                     │     │              │     │                   │
│  Compile from src:  │     │  Build OCI   │     │  Download Fedora  │
│  - libcomposefs     │     │  image from  │     │  netinstall ISO   │
│  - libostree        │     │  Containerfile│    │  Inject branding  │
│  - bootupd          │     │              │     │  Render kickstart │
│  - grub-efi-signed  │     │  Push to     │     │  Build online ISO │
│  - bootc            │     │  GHCR        │     │  Build offline ISO│
│  - firstboot-setup  │     │              │     │                   │
│  - ifupdown2 repack │     │  Sign with   │     │  Upload to        │
│  - timesyncd repack │     │  cosign      │     │  GitHub Releases  │
│                     │     │              │     │                   │
│  Publish APT repo   │     │  Smoke test: │     │                   │
│  to GitHub Pages    │     │  bootc lint  │     │                   │
└─────────────────────┘     └──────────────┘     └───────────────────┘
```

The **Full Pipeline** workflow (`pipeline.yml`) orchestrates all three stages with
optional per-stage toggles, useful for rebuilding only the component that changed
without running the full 30+ minute pipeline.

### Why GitHub Actions are not pinned to commit SHAs

Pinning actions to commit SHAs provides supply-chain immutability against tag
mutation, but shifts the entire maintenance burden onto the repository owner: every
dependency update requires a manual SHA rotation. In practice this leads to
perpetually outdated pins — which provide false security rather than real security.

This repository instead relies on **Dependabot** (`.github/dependabot.yml`) for
weekly automated pull requests covering both GitHub Actions and the Docker base image.
Updates are reviewed and merged explicitly, providing full auditability without
manual tracking overhead. All actions used are from well-established, high-visibility
namespaces (`actions/*`, `sigstore/*`, `morph027/*`) where tag mutation would be
immediately detected by the community.

---

## APT repository

The custom packages are published to a signed APT repository on GitHub Pages.
The signing key SHA-256 is hardcoded in the Containerfile and verified at build
time before the key is trusted.

Add to an existing Debian Trixie system:

```bash
wget -O /usr/share/keyrings/debian-bootc-keyring.gpg \
  https://daemoncores.github.io/debian-bootc/gpg.key

# Optionally verify the key fingerprint before trusting it:
sha256sum /usr/share/keyrings/debian-bootc-keyring.gpg

cat > /etc/apt/sources.list.d/debian-bootc.sources << 'EOF'
Types: deb
URIs: https://daemoncores.github.io/debian-bootc/
Suites: trixie
Components: main
Enabled: yes
Signed-By: /usr/share/keyrings/debian-bootc-keyring.gpg
EOF

apt update
```

---

## Secure Boot

This image supports UEFI Secure Boot via the standard MOK (Machine Owner Key)
mechanism provided by `shim-signed`.

### Chain of trust

UEFI firmware → shim-signed (Microsoft-signed) → grubx64.efi (debian-bootc-signed) → kernel

The `grub-efi-amd64-signed` package includes:
- A GRUB EFI binary signed with the debian-bootc Secure Boot signing key.
- The signing certificate at `/usr/share/debian-bootc/sb_signing.crt`.
- A `postinst` script that queues MOK enrollment automatically on package install.

### Enrollment

MOK enrollment is queued automatically. On the **first reboot** after installation,
the firmware will launch the blue MokManager screen:

1. Select **Enroll MOK**
2. Select **Continue**
3. Select **Yes**
4. Enter the enrollment password when prompted
5. Select **Reboot**

The signing key is then enrolled permanently. All subsequent boots are fully
verified end-to-end without any further action.

### Verify enrollment

```bash
mokutil --sb-state          # confirm Secure Boot is active
mokutil --list-enrolled     # confirm the debian-bootc key is present
```

---

## Required secrets

| Secret           | Workflow                    | Purpose                                           |
|------------------|-----------------------------|---------------------------------------------------|
| `PAT_PKG`        | `bootc-build.yml`           | Authenticate Podman and Docker to push to GHCR    |
| `APT_GPG_KEY`    | `bootc-debs-builder.yml`    | Sign the APT repository published to GitHub Pages |
| `SB_SIGNING_KEY` | `bootc-debs-builder.yml`    | Private key for GRUB EFI Secure Boot signing      |
| `SB_SIGNING_CERT`| `bootc-debs-builder.yml`    | Certificate for GRUB EFI Secure Boot signing      |

---

## Quick start

1. Fork this repository.
2. Add `PAT_PKG` and `APT_GPG_KEY` in **Settings → Secrets → Actions**.
3. Run **Actions → Full Pipeline** with all three stages enabled.
4. Download the produced ISO from the `install-iso` release.
5. Boot the ISO on the target machine and follow the first-boot wizard.

For monthly automated rebuilds, the `pipeline.yml` schedule (`0 4 1 * *`) will
trigger automatically once the repository is active.

---

## License

[LGPL-2.1](LICENSE)