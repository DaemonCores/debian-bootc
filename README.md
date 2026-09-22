# debian-bootc

<p align="center">
  <img src="https://raw.githubusercontent.com/DaemonCores/.github/refs/heads/main/assets/banner.svg" alt="AstralEmu Banner" width="100%"/>
</p>

<p>
  <strong align="left">Simplify and Innovate for Everyone.</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
  
  <em>Identify gaps and fill them, make improvements where possible, but above all, empower developers to offer more to users.</em>
</p>

---

`debian-bootc` builds Debian 13 as a bootc/OSTree operating-system image. It packages the bootc stack that is not provided by Debian, assembles OCI images, boots them under QEMU for runtime validation, and generates installer artifacts.

The repository is under active development. The amd64 path is the current installation target; arm64 image, package, and disk-image work is present in the pipeline but should be treated as being validated until the architecture matrix is explicitly released.

## Implemented components

- Debian packages for bootc, OSTree, composefs, bootupd, a BLS-capable GRUB build, first-boot setup, and bootc-specific service integration.
- A signed APT repository published from the package manifest in `workflows/bootc-debs-builder/packages.yml`.
- A full image and a reduced `minimal` image assembled from Debian Trixie.
- Native amd64 and arm64 jobs in the shared CI, content-addressed package reuse, GHCR publication, and keyless cosign signing.
- Boot tests that install an image to a virtual disk, start it with QEMU/KVM, and execute `workflows/image-tests/tests.yml` over SSH before publication.
- Online and offline amd64 installer ISOs.
- Optional raw image generation for the targets enabled by the caller workflow.

## Image variants

| Source | Tag family | Purpose |
| --- | --- | --- |
| `Containerfile` | `latest` | General-purpose Debian bootc system with SSH, Podman, ifupdown2, firmware, troubleshooting tools, and the first-boot wizard. |
| `Containerfile.minimal` | `minimal` | Reduced system using systemd-networkd, a smaller package set, non-persistent journald storage, and masked background services. |

The minimal Containerfile declares both automatic-update and lock variants. The CI publishes architecture-specific tags and then creates manifest-list tags after successful builds.

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
| `PAT_PKG` | Pull and publish images in GHCR. |
| `APT_GPG_KEY` | Sign the generated APT repository. |
| `SB_SIGNING_KEY` | Sign the custom EFI bootloader package. |
| `SB_SIGNING_CERT` | Certificate paired with the Secure Boot key. |

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
