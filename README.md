# debian-bootc

<p align="center">
  <img src="https://raw.githubusercontent.com/DaemonCores/.github/refs/heads/main/assets/banner.svg" alt="DaemonCores Banner" width="100%"/>
</p>

<p>
  <strong>A foundation for building immutable, Debian-based distributions.</strong><br/>
  <em>Bring the atomic operating-system model to the Debian ecosystem, server side included.</em>
</p>

<p>
  <a href="https://github.com/DaemonCores/debian-bootc"><img src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a> <a href="https://github.com/orgs/DaemonCores/discussions"><img src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a> <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
</p>

---

> **Developer Alpha.** Debian bootc is an early developer alpha. Its OCI base image is installable and usable as a minimal Debian system, with no graphical interface, intended for customization and downstream distributions. The project is under active development and its CI/CD pipeline is currently being debugged: previous builds have been produced and installed, but the current build and release automation must not yet be considered reliable. The installer ISOs published in the Releases are known to be broken; no working installer ISO is available at this time.

## What this is

Debian bootc is a **foundation**: a Debian 13 base built on bootc/OSTree that other projects take as a template to build their own specialised immutable systems. It is not a desktop distribution and it does not choose a graphical environment, a package set or a use case for you. Derived images pick their own packages, services, interface and specialisation; the foundation does the hard shared work once (the bootc stack Debian does not package, the boot chain, signing, boot tests) so derivatives can concentrate on what makes them different.

The ambition is comparable to the Debian / derivative relationship (Debian is the base from which Ubuntu and many others inherit), applied to immutable systems. The comparison describes the goal of the ecosystem only: Debian bootc is not an official Debian fork and its technical model is not that of Ubuntu.

### Why Debian, and why the server side

Fedora Atomic and Universal Blue are different, mature approaches; this project does not aim to replace them and the audiences can overlap. What Debian bootc adds is **access to the Debian ecosystem**. A large amount of server and infrastructure software is packaged, documented and maintained first for Debian and APT, and moving it to Fedora-based atomic tooling is often impractical. The question the project works on is: *how do we give the properties of an atomic bootc/OSTree system to software that already lives on Debian?*

[DaemonCores-VE](https://github.com/DaemonCores/DaemonCores-VE) (Proxmox VE as an atomic image, built through [`proxmox-ve-bootc`](https://github.com/DaemonCores/proxmox-ve-bootc)) is a concrete example of this direction. The foundation itself stays generic and is not tied to Proxmox.

### What it is not

- not a replacement for Fedora Atomic or Universal Blue;
- not a desktop distribution (no GNOME, KDE or other environment is imposed);
- not a single final product every user must conform to;
- not a promise that any Debian software runs unchanged in an atomic system: adaptation is expected;
- not a project whose CI/CD is currently fully operational.

## Who it is for

Right now the project looks for people who want to **build, maintain or contribute to immutable Debian distributions**: distribution and specialised-system developers, people interested in bootc, OSTree, composefs and Debian integration, maintainers of server software in the Debian ecosystem, administrators able to test server use cases and report technically, and contributors on documentation, tests, packages and tooling. It is not yet aimed at end users looking for a ready-to-install desktop.

## Current status

| Item | State |
| --- | --- |
| OCI base image | Installable and usable as a base system. A blank Debian template: no graphical interface, mainly meant to be derived. CLI use is possible. |
| Derived images | Central architectural principle. The template repository is [`debian-bootc-template`](https://github.com/DaemonCores/debian-bootc-template); see [Deriving an image](#deriving-an-image). |
| CI/CD | Being debugged. The latest Full Pipeline runs on `main` are not all green; do not read earlier successful builds as validating the current state. |
| Release channels | Separating release channels with a git-flow model is a requirement of the ongoing CI rework, not yet in place. |
| Installer ISOs | The ISOs attached to the `install-iso` release are known to be broken. The offline ISO cannot be hosted as a release asset because of its size. No working installer ISO is available. |
| Graphical demo distribution | Planned; its repository does not exist yet. |
| Other projects | See [Ecosystem](#ecosystem). |

## Ecosystem

The projects below illustrate directions built on or around the foundation; they do not share the same maturity.

- **Debian bootc** (this repository): the foundation.
- **[DaemonCores-VE](https://github.com/DaemonCores/DaemonCores-VE)**: the server direction, Proxmox VE on top of this foundation, through the intermediate `proxmox-ve-bootc` image. It is itself in active development and depends on the base being fixed.
- **A graphical distribution** built from the template is envisaged, with no repository yet.

## Deriving an image

The intended path is to create a repository from [`debian-bootc-template`](https://github.com/DaemonCores/debian-bootc-template): its `Containerfile` starts `FROM` this base, overlays and Debian packages are declared in `src/overlay/` and `workflows/bootc-debs-builder/packages.yml`, and the shared pipeline builds, boot-tests and publishes the result. The structure is the same one `proxmox-ve-bootc` and `DaemonCores-VE` already use on top of this base, which is the reason it is considered valid.

Verification status: the template itself cannot currently be expected to work end to end, because the base it derives from is being repaired. Treat the template's steps as **documented but to be re-tested**, not as a verified tutorial.

> **Notice for existing installations.** Until now the images were signed keyless, which a host cannot require, so installed systems accept whatever the registry serves. Images now carry a signature policy: hosts require this repository's cosign signature for `ghcr.io/daemoncores/debian-bootc`. Hosts installed before this change have no such policy; they pick it up with the first update to an image built after the signing key exists, and that update is the last one they accept without verification. If you installed from this repository and want to be sure, reinstall from a fresh image or check `/etc/containers/policy.json` after updating. If the signing key is ever regenerated, hosts that pinned the old public key refuse new images until they are reinstalled or their `/etc/pki/containers/image-signing.pub` is replaced.

## Technical overview

`debian-bootc` builds Debian 13 as a bootc/OSTree operating-system image. It packages the bootc stack that is not provided by Debian, assembles OCI images, boots them under QEMU for runtime validation, and generates installer artifacts.

The repository is under active development. The amd64 path is the current installation target; arm64 image, package, and disk-image work is present in the pipeline but should be treated as being validated until the architecture matrix is explicitly released.

## Implemented components

Components present in the repository; the current pipeline that builds them is under repair (see [Current status](#current-status)).

- Debian packages for bootc, OSTree, composefs, bootupd, a BLS-capable GRUB build, and bootc-specific service integration.
- A signed APT repository published from the package manifest in `workflows/bootc-debs-builder/packages.yml`.
- A full image assembled from Debian Trixie (the NVIDIA stack is derived at install time, never hosted as a separate image).
- Native amd64 and arm64 jobs in the shared CI, content-addressed package reuse, GHCR publication, and cosign signing with a key owned by the repository.
- Boot tests that install an image to a virtual disk, start it with QEMU/KVM, and execute `workflows/tests.yml` over SSH before publication.
- Installer ISO generation (live installer image `Containerfile.iso`). The ISOs currently attached to the Releases are known to be broken.
- Optional raw image generation for the targets enabled by the caller workflow.

## Image variants

| Source | Tag family | Purpose |
| --- | --- | --- |
| `Containerfile` | `latest` | General-purpose Debian bootc system with SSH, Podman, ifupdown2, firmware, troubleshooting tools. The first-boot wizard is replaced: user, root password, sudo, ssh policy, hostname, hosts, locale and keyboard are set at install by bootc-installer. |

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
make build  # builds the local base then the image
```

or directly, once `make build-base` (or any base at `localhost/debian-bootc-base:latest`) exists:

```bash
podman build --format docker \
  --build-arg PRODUCT_NAME="debian bootc" \
  -f Containerfile \
  -t debian-bootc:local .
```

The build downloads the repository signing key, verifies its pinned SHA-256 digest, and consumes packages from the project's APT repository. See [`docs/building.md`](docs/building.md) for the architecture-specific build arguments.

## Installation

No working installer ISO is available at the moment: the ISOs on the `install-iso` release are known to be broken, and the offline ISO is too large to be hosted as a release asset. The base image itself is the supported entry point for now (see [Current status](#current-status)).

The installer design below describes what the installer does once ISO generation is repaired. It performs its own interactive target-disk selection and uses `bootc install to-filesystem`. It creates EFI and `/boot` partitions plus a Btrfs pool with separate `root`, `var`, and `varlog` subvolumes. Reinstallation can preserve the existing `var` subvolume.

The installer is destructive to the selected disk. Review the prompt carefully and test in a virtual machine before using it on physical hardware.

## Try it in a VM

The published image can be installed on a virtual disk and booted exactly as the CI does it, with the CI's own harness ([`DaemonCores-CI/image-test`](https://github.com/DaemonCores/DaemonCores-CI/tree/main/image-test)). This needs rootful podman, QEMU, OVMF and `sudo`; nothing touches a real disk (a sparse raw file is used).

```bash
git clone https://github.com/DaemonCores/DaemonCores-CI
export IMAGE=ghcr.io/daemoncores/debian-bootc:latest
export IMAGE_TEST_STATE="$PWD/vm-state"        # holds the raw disk, keys, OVMF vars
sudo -E podman pull "$IMAGE"
sudo -E bash DaemonCores-CI/image-test/image-test.sh prepare
sudo -E bash DaemonCores-CI/image-test/image-test.sh test "$IMAGE"
```

`test` partitions the disk (ESP, `/boot`, Btrfs pool), runs `bootc install to-filesystem` from the image, boots it under QEMU with UEFI Secure Boot and runs the checks of [`workflows/tests.yml`](workflows/tests.yml). The installed disk is left in `$IMAGE_TEST_STATE/test-disk.raw`.

![Console of the installed image booted in QEMU](assets/demo/boot-console.png)

*Real console of the installed `:latest` image (kernel `7.2.15-x64v1-xanmod1`, Secure Boot on).*

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
(`workflows/bootc-debs-builder/bootc-installer-src`) runs the
live-image helper `/usr/libexec/debian-bootc/mok-stage` through `pkexec`. The
helper queues `/usr/share/debian-bootc/sb_signing.crt` with `mokutil --import`
and a random one-time password, which the installer shows on its
acknowledgement page. At the first reboot, the blue MokManager screen asks for
that password: *Enroll MOK, Continue, Yes, enter the password, Reboot*. Nothing
is queued on BIOS machines or when the certificate is already enrolled.

GitHub Pages must be configured for Actions deployment so the APT repository can be published.

## Development practices

Debian bootc is developed with extensive use of AI coding assistants. The architecture, requirements and acceptance decisions are the maintainer's; the maintainer validates behaviour by testing on real hardware, but does not review every generated line. Generated code is not assumed correct because it compiles. Independent testing and technical scrutiny are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation

- [Architecture](docs/Handoff-Architecture.md)
- [Design decisions and security trade-offs](docs/Handoff-Decisions.md)
- [Building images and the kernel](docs/building.md)
- [Support](SUPPORT.md)
- [Security policy](SECURITY.md)

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
