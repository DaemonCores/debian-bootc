# debian-bootc

<p align="center">
  <img src="https://raw.githubusercontent.com/DaemonCores/.github/refs/heads/main/assets/banner.svg" alt="DaemonCores Banner" width="100%"/>
</p>

<p>
  <strong align="left">Simplify and Innovate for Everyone.</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
  
  <em>Identify gaps and fill them, make improvements where possible, but above all, empower developers to offer more to users.</em>
</p>

---

> **Notice for existing installations.** Until now the images were signed keyless, which a host cannot require, so installed systems accept whatever the registry serves. Images now carry a signature policy: hosts require this repository's cosign signature for `ghcr.io/daemoncores/debian-bootc`. Hosts installed before this change have no such policy; they pick it up with the first update to an image built after the signing key exists, and that update is the last one they accept without verification. If you installed from this repository and want to be sure, reinstall from a fresh ISO or check `/etc/containers/policy.json` after updating. If the signing key is ever regenerated, hosts that pinned the old public key refuse new images until they are reinstalled or their `/etc/pki/containers/image-signing.pub` is replaced.

`debian-bootc` builds Debian 13 as a bootc/OSTree operating-system image. It packages the bootc stack that is not provided by Debian, assembles OCI images, boots them under QEMU for runtime validation, and generates installer artifacts.

The repository is under active development. The amd64 path is the current installation target; arm64 image, package, and disk-image work is present in the pipeline but should be treated as being validated until the architecture matrix is explicitly released.

## Implemented components

- Debian packages for bootc, OSTree, composefs, bootupd, a BLS-capable GRUB build, first-boot setup, and bootc-specific service integration.
- A signed APT repository published from the package manifest in `workflows/bootc-debs-builder/packages.yml`.
- A full image and a reduced `minimal` image assembled from Debian Trixie.
- Native amd64 and arm64 jobs in the shared CI, content-addressed package reuse, GHCR publication, and cosign signing with a key owned by the repository.
- Boot tests that install an image to a virtual disk, start it with QEMU/KVM, and execute `workflows/tests.yml` over SSH before publication.
- Online and offline amd64 installer ISOs.
- Optional raw image generation for the targets enabled by the caller workflow.

## Image variants

| Source | Tag family | Purpose |
| --- | --- | --- |
| `Containerfile` | `latest` | General-purpose Debian bootc system with SSH, Podman, ifupdown2, firmware, troubleshooting tools, and the first-boot wizard. |
| `Containerfile.minimal` | `minimal` | Reduced system using systemd-networkd, a smaller package set, non-persistent journald storage, and masked background services. |

Each image is published once per tag, with automatic updates on by default (a symlink in `/etc` switches them off). The CI publishes architecture-specific tags and then creates manifest-list tags after successful builds.

## Pipeline

The repository's `pipeline.yml` is a thin caller for [`DaemonCores-CI`](https://github.com/DaemonCores/DaemonCores-CI):

1. build the package environment;
2. build amd64 and arm64 Debian packages in dependency waves;
3. publish the signed APT repository;
4. build every root-level `Containerfile*` variant;
5. boot and test each image before it is pushed;
6. sign published images and assemble multi-architecture manifests;
7. build the selected installer and disk-image artifacts.

Pushes use change detection to skip unaffected stages. A scheduled run performs a full rebuild on the first day of each month. Manual runs expose stage-selection inputs.

## Build locally

The full image can be assembled on an amd64 host with:

```bash
podman build --format docker \
  --build-arg PRODUCT_NAME="debian bootc" \
  -f Containerfile \
  -t debian-bootc:local .
```

The build downloads the repository signing key, verifies its pinned SHA-256 digest, and consumes packages from the project's APT repository. See [`docs/minimal.md`](docs/minimal.md) for the minimal image's architecture-specific arguments.

## Installation

When a successful `install-iso` release is available, use the online ISO for a registry-backed installation or the offline ISO when the image must be embedded in the installation media.

The installer performs its own interactive target-disk selection and uses `bootc install to-filesystem`. It creates EFI and `/boot` partitions plus a Btrfs pool with separate `root`, `var`, and `varlog` subvolumes. Reinstallation can preserve the existing `var` subvolume.

The installer is destructive to the selected disk. Review the prompt carefully and test in a virtual machine before using it on physical hardware.

## Required repository configuration

| Secret | Purpose |
| --- | --- |
| `PAT_SECRETS` | Token with `secrets:write`. The only secret a fork has to provide: the `prepare` stage uses it to generate all the others on the first run, then restarts the pipeline so they are visible. |
| `PAT_PKG` | Optional. Pull and publish images in GHCR; defaults to the workflow token. |
| `APT_GPG_KEY` | Signs the generated APT repository. Generated automatically. The image build derives the key pin from it, nothing is committed. |
| `SB_SIGNING_KEY`, `SB_SIGNING_CERT` | Self-signed Secure Boot key and certificate for the custom EFI bootloader package. Generated automatically; firmware only trusts the certificate once it is enrolled (MOK or db). |
| `COSIGN_PRIVATE_KEY`, `COSIGN_PASSWORD`, `COSIGN_PUBLIC_KEY` | Image signing key of this repository. Generated automatically; a fork gets its own key and its own signed images. |
| `MODULE_SIGNING_KEY`, `MODULE_SIGNING_CERT` | Kernel module signing key. Generated automatically when module signing is enabled. When it is active the kernel build also enforces signatures (`MODULE_SIG_FORCE`) and builds the secondary and machine keyrings; when it is not, nothing is signed and nothing is forced. |

Without `PAT_SECRETS` nothing is generated: images are signed keyless and modules stay unsigned. The workflow needs `actions: write` so `prepare` can restart the pipeline.

### Secure Boot enrollment during install

A fork keeps its own key: drop the public certificate of that key in
`src/buildisopreinstall/usr/share/debian-bootc/mok.d/` (`*.crt`, `*.cer`,
`*.pem`, `*.der`). The installer reads that directory at install time and
enrolls every certificate in one `mokutil --import`, so there is a single
MokManager password. Files holding a private key are refused; never
distribute private keys.

The installer enrolls the signing certificate for you. After a successful
install on a UEFI machine, the patched `bootc-installer`
(`workflows/bootc-debs-builder/patches/bootc-installer-mok.patch`) runs the
live-image helper `/usr/libexec/debian-bootc/mok-stage` through `pkexec`. The
helper queues `/usr/share/debian-bootc/sb_signing.crt` with `mokutil --import`
and a random one-time password, which the installer shows on its
acknowledgement page. At the first reboot, the blue MokManager screen asks for
that password: *Enroll MOK, Continue, Yes, enter the password, Reboot*. Nothing
is queued on BIOS machines or when the certificate is already enrolled.

GitHub Pages must be configured for Actions deployment so the APT repository can be published.

## Documentation

- [Architecture](docs/architecture.md)
- [Design decisions and security trade-offs](docs/justifications.md)
- [Minimal image](docs/minimal.md)
- [Support](SUPPORT.md)
- [Security policy](SECURITY.md)

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
