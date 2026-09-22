# Architecture

## Scope

`debian-bootc` supplies the Debian base used by the DaemonCores image projects. It combines four concerns that must remain synchronized:

1. Debian packages for the bootc stack;
2. bootable OCI image definitions;
3. runtime validation of the built system;
4. installation and publication artifacts.

The project targets Debian 13 (Trixie). `DaemonCores-VE` consumes the published `latest` image as its base.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `Containerfile` | General-purpose image. |
| `Containerfile.minimal` | Reduced multi-architecture image definition. |
| `src/` | Files copied into the image before and after package installation. |
| `workflows/bootc-debs-builder/` | Package manifest, build scripts, package metadata, and overlays. |
| `workflows/build-env/env.yml` | Package-builder environment recipe. |
| `workflows/image-tests/tests.yml` | Tests executed against a booted image. |
| `kernel/` and `modules-kernel/` | Kernel and device-module configuration inputs. |
| `.github/workflows/pipeline.yml` | Product-specific triggers for the shared pipeline. |

## Package layer

The package manifest is read by the shared `bootc-debs-builder.yml` workflow. Dependencies are converted into topological waves so independent packages build in parallel and dependent packages consume artifacts from earlier waves.

The current manifest covers:

- `bootc`, `ostree`, `libcomposefs`, and `bootupd`;
- the signed amd64 GRUB package;
- the first-boot setup package;
- bootc-aware repacks of ifupdown2 and systemd-timesyncd;
- the common kernel image and architecture/device module packages.

Package inputs are hashed. When the source overlay, upstream version, build script, and non-secret environment are unchanged, the previous package is restored from the published cache instead of rebuilt. The resulting repository is signed and deployed to GitHub Pages.

## Image layer

The full image installs the package stack, kernel, firmware, SSH, Podman, system administration tools, ifupdown2, and first-boot setup. The minimal image deliberately omits most interactive and server tooling; see [Minimal image](minimal.md).

Both images adapt the filesystem layout for OSTree:

- `/home`, `/root`, `/mnt`, `/srv`, and `/opt` resolve into `/var`;
- `/ostree` resolves into `/sysroot/ostree`;
- locale state is moved into writable storage;
- `/usr` is supplied by the deployment while `/etc` and `/var` remain writable.

## Build and test flow

The shared image workflow discovers every root-level `Containerfile*` and derives the tag family from its filename. It schedules native runner jobs for each architecture and update variant.

For every matrix entry the workflow:

1. computes an input hash from the Containerfiles, published package metadata, base-image digest, architecture, and update mode;
2. builds the OCI image with Podman;
3. runs bootc validation;
4. installs the image onto a virtual disk;
5. boots that disk with QEMU/KVM and UEFI firmware;
6. executes every applicable test from `workflows/image-tests/tests.yml` over SSH;
7. pushes and signs the image only after the tests pass.

Tests cover the bootc deployment, OSTree and composefs mounts, writable state, bootloader assets, initramfs contents, networking, package repacks, and first-boot tooling. Architecture-specific checks are gated in the test manifest.

## Tags and manifests

Architecture-specific tags follow this shape:

```text
<variant>_<arch>_<autoupdate|lock>
```

Examples include `latest_amd64_autoupdate`, `minimal_arm64_autoupdate`, and `minimal_amd64_lock`. After all architecture jobs succeed, the workflow publishes manifest-list aliases such as `latest`, `minimal`, `minimal_autoupdate`, and `minimal_lock` where applicable.

## Installation media

The ISO workflow currently targets amd64. It starts from a Fedora Server net-install environment because Anaconda provides the installer runtime used by the project.

The Kickstart runs the actual installation from `%pre`:

- the operator selects the target disk;
- the installer creates EFI, ext4 `/boot`, and Btrfs system partitions;
- the Btrfs pool contains `root`, `var`, and `varlog` subvolumes;
- `/var/log` receives a 2 GiB qgroup limit;
- `bootc install to-filesystem` deploys the image;
- an existing compatible pool may keep its `var` subvolume during reinstall.

The online ISO pulls the registry image during installation. The offline ISO embeds an OCI archive. Both retain the registry reference as the future upgrade source.

## Trust boundaries

- APT repositories use an explicit signing key whose downloaded bytes are checked against a pinned SHA-256 value in the Containerfile.
- GHCR images are signed with cosign using the GitHub Actions OIDC identity.
- The custom EFI package is built with the configured Secure Boot key and certificate.
- Runtime tests execute before image publication, but they do not replace hardware qualification.
- The installer runs privileged storage operations and must be tested carefully before physical deployment.

## Current architecture boundary

The CI and package manifests contain arm64 support work, but the installer ISO remains amd64-only and the complete architecture/tag matrix is still being validated. A repository path or generated matrix entry is not, by itself, a support guarantee.
