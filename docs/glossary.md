# Glossary

Terms used across `debian-bootc` code, CI and docs. One line per term; follow the link for detail.

## Architecture

| Term | Definition |
|------|------------|
| bootc | Bootable OCI container tooling: the OS is shipped as a container image and deployed/updated by `bootc`; built from source here as a `.deb` [src: file: workflows/bootc-debs-builder/packages.yml:1009]. See [architecture](architecture.md). |
| OSTree | Content-addressed object store for bootable OS trees; provides the atomic `/usr` deployment [src: file: workflows/bootc-debs-builder/preinstall/output/ostree/DEBIAN/control:13]. |
| composefs / libcomposefs | Integrity-protected filesystem image library used by OSTree; enabled for the root via `[composefs] enabled=yes` [src: file: workflows/bootc-debs-builder/ostreepostinstall/usr/lib/ostree/prepare-root.conf:5]. |
| `prepare-root.conf` | OSTree config shipped in the `ostree` deb: read-only sysroot plus composefs root [src: file: workflows/bootc-debs-builder/ostreepostinstall/usr/lib/ostree/prepare-root.conf:1]. |
| OSTree filesystem layout | `/home`, `/root`, `/mnt`, `/srv`, `/opt` are symlinks into `/var` so the read-only `/usr` can be swapped atomically [src: file: Containerfile:107]. See [justifications § OSTree filesystem layout](justifications.md#ostree-filesystem-layout). |
| bootupd | Cross-distribution EFI bootloader update manager [src: file: workflows/bootc-debs-builder/preinstall/output/bootupd/DEBIAN/control:13]. |
| BLS | Boot Loader Specification entries; the custom GRUB is built with BLS support for the deployment model [src: file: workflows/bootc-debs-builder/preinstall/output/grub-efi-amd64-signed/DEBIAN/control:12]. |
| dracut | Initramfs generator used for the bootc/OSTree boot path [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:5]. |
| `bootc-finalize` | Build-time script: moves the newest kernel into `/usr/lib/modules/<kver>`, regenerates the initramfs and stages signed shim/GRUB EFI binaries for bootupd [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:3]. |
| `zz-bootc-finalize` | Kernel `postinst.d` hook shipped in the `bootc` deb so downstream images that install/update a kernel get it finalized [src: file: workflows/bootc-debs-builder/bootcpostinstall/etc/kernel/postinst.d/zz-bootc-finalize:3]. |
| bootc lint | bootc's image validation; fails if a second `/usr/lib/modules/<kver>/` exists (hence no stock Debian kernel) [src: file: Containerfile:48]. |
| `policy-rc.d` | Build-time hook returning `101` so no daemon starts inside the build container; removed at the end of the build [src: file: src/debianpreinstall/usr/sbin/policy-rc.d:3] [src: file: Containerfile.minimal:154]. |
| Preinstall / postinstall overlay | `src/*preinstall/` and `src/*postinstall/` trees copied into the image before/after package installation; `workflows/bootc-debs-builder/*postinstall/` are the equivalent per-package overlays [src: file: Containerfile:157] [src: file: docs/architecture.md:20]. See [architecture § Repository layout](architecture.md#repository-layout). |
| Full image (`main` variant) | General-purpose image defined by `Containerfile` [src: file: Containerfile.base:10]; called `main` in test gating [src: file: workflows/tests.yml:19]. |
| Minimal image | Reduced image contract defined by `Containerfile.minimal` (networkd, no SSH/Podman, no persistent journal) [src: file: Containerfile.minimal:23]. See [minimal](minimal.md). |
| Automatic updates | Always on: the bootc package enables `bootc-fetch-apply-updates.timer`. A symlink `/etc/systemd/system/bootc-fetch-apply-updates.timer -> /dev/null` switches them off; there is no separate lock image. |
| `org.daemoncores.unsigned-kernel-image` | Image label asking the CI for a `<tag>-nosign` twin that installs the unsigned kernel (`both` signing mode) [src: file: Containerfile:20]. |
| Image tag | `<tag>_<arch>` per architecture, plus the manifest-list tags such as `latest`, `minimal` [src: file: docs/architecture.md:73]. `Containerfile.iso` uses the same form [src: file: Containerfile.iso:28]. |
| Kernel variant (`KERNEL_VARIANT`) | Build arg selecting the kernel package `linux-image-${KERNEL_VARIANT}-${ARCH}`; default `minimal`, used by both images [src: file: Containerfile.minimal:145]. |
| `linux-image-minimal-<arch>` | Virtual package name provided by the project's custom kernel deb `daemoncores-kernel-<kver>` [src: file: workflows/bootc-debs-builder/packages.yml:233]. |
| Kernel module packages | `linux-modules-arm-device` (one package per device: `linux-modules-rpi3`, `-rpi4`, `-rpi5`, `-rk3588`), built from the `kernel/modules/<device>` overlays on top of the kernel's own `.config`; the `kernel/modules/arm` and `x86_64` overlays are merged into the kernel build `linux-image` [src: file: workflows/bootc-debs-builder/packages.yml:333] [src: file: workflows/bootc-debs-builder/kernel/modules/rk3588:5]. |
| `BOOT_PKG` | Build arg for the boot package: `grub-efi-amd64-signed` on amd64, `grub-efi-arm64-signed` on arm64 generic, `u-boot-tools` on arm64 embedded [src: file: Containerfile.minimal:97]. |
| `PRODUCT_NAME` | Build arg written to `/usr/lib/bootc/product-name`, consumed by boot finalization tooling [src: file: Containerfile.base:56]. |
| `BOOTC_GPG_SHA256` | SHA-256 of the APT signing key, derived by the CI from `APT_GPG_KEY` and checked during the build [src: file: Containerfile:54] [src: file: Containerfile.base:33]. |
| Package manifest | `workflows/bootc-debs-builder/packages.yml`: one entry per `.deb` with `name`, `upstream`, `deps`, `sources`, `deb-glob`, `env`, `secret-env`, `build` [src: file: workflows/bootc-debs-builder/packages.yml:2]. |
| Repack | Package built from an existing Debian package (`upstream` field) plus a bootc overlay, e.g. ifupdown2, systemd-timesyncd [src: file: workflows/bootc-debs-builder/packages.yml:5] [src: file: workflows/bootc-debs-builder/packages.yml:625]. |
| Wave | Group of packages with no pending `deps`, built in parallel; `deps` create later waves [src: file: workflows/bootc-debs-builder/packages.yml:3] [src: file: workflows/bootc-debs-builder/packages.yml:6]. |
| Content cache | Per-deb reuse: declared `sources` and `env` are hashed; unchanged packages are restored instead of rebuilt [src: file: workflows/bootc-debs-builder/packages.yml:7] [src: file: workflows/bootc-debs-builder/packages.yml:9]. See [justifications § Content-addressed package reuse](justifications.md#content-addressed-package-reuse). |
| Buildenv | Toolchain image `ghcr.io/<owner>/<repo>-buildenv` assembled with buildah from `workflows/env.yml`; package builds run inside it [src: file: workflows/env.yml:5]. |
| Test manifest | `workflows/tests.yml`: tests run over SSH on a QEMU/KVM boot of the installed image; failure blocks the push [src: file: workflows/tests.yml:1]. |
| `diag` | Required per-test command run over SSH on failure to capture state; missing `diag` fails the build [src: file: workflows/tests.yml:9]. |
| `arch` / `variant` gates | Optional test fields restricting a test to `amd64`/`arm64` or `main`/`minimal`; mismatches report SKIP [src: file: workflows/tests.yml:13] [src: file: workflows/tests.yml:19]. |
| Thin caller | `.github/workflows/pipeline.yml` only declares triggers/concurrency and calls the shared `full-pipeline.yml` [src: file: .github/workflows/pipeline.yml:3]. |
| Stage / auto-skip | Pipeline stages (env, debs, image, iso, img) skipped on push when untouched; manual runs select stages via `run_*` inputs [src: file: .github/workflows/pipeline.yml:8] [src: file: .github/workflows/pipeline.yml:27]. |
| Module signing mode | `nosign` / `sign` / `both`, default from `config.yml`, overridable via the `sign_modules` dispatch input [src: file: config.yml:4] [src: file: config.yml:11]. |

## Domain

| Term | Definition |
|------|------------|
| firstboot-user-setup | First-boot TUI on tty1 that creates the user account and sets the root password [src: file: workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:3]. See [justifications § First-boot credential provisioning](justifications.md#first-boot-credential-provisioning). |
| `ifupdown2-autoconf` | Boot-time generator for `/etc/network/interfaces` (DHCP on first ethernet NIC, DHCPv6 probe); runs only while its marker line is present [src: file: workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf:3]. |
| `domain-set` | Renders `/etc/hosts` and `/etc/issue` from templates using the global IPv4, short hostname and DHCP domain [src: file: workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:3]. |
| Networking profiles | Full image uses ifupdown2; minimal image uses systemd-networkd [src: file: docs/justifications.md:31]. |
| Installer ISO | Live image from `Containerfile.iso` (cage + bootc-installer + fisherman) converted to ISO by bootc-image-builder [src: file: Containerfile.iso:5]. See [architecture § Installation media](architecture.md#installation-media). |
| Online / offline ISO | Online ISO pulls the registry image during install; offline ISO embeds an OCI archive [src: file: docs/architecture.md:97]. |
| bootc-installer | Graphical GTK4 frontend for bootc OS installation [src: file: workflows/bootc-debs-builder/preinstall/output/bootc-installer/DEBIAN/control:20]. |
| fisherman | bootc disk installer backend (Go), run by the live user via `pkexec` [src: file: workflows/bootc-debs-builder/preinstall/output/fisherman/DEBIAN/control:10] [src: file: Containerfile.iso:13]. |
| Recipe | `recipe.json` listing installable images for the installer, regenerated by `scripts/gen-recipe.py` [src: file: scripts/gen-recipe.py:2]. |
| Live user | ISO user autologged on tty1 that launches cage → bootc-installer [src: file: Containerfile.iso:12]. |
| Gallium | Optional arm64 "Linux Gallium .img" stage of the shared pipeline, disabled in this repo (no Gallium phone target) [src: file: .github/workflows/pipeline.yml:49] [src: file: .github/workflows/pipeline.yml:79]. <!-- TODO: ask user --> |

## Environments

| Term | Definition |
|------|------------|
| amd64 | Current installation target; ISO is amd64-only [src: file: README.md:20] [src: file: docs/architecture.md:109]. |
| arm64 | Supported in CI/manifests but still being validated; uses U-Boot instead of GRUB [src: file: README.md:20] [src: file: Containerfile.minimal:97]. |
| SBC targets | Kernel module overlays for Raspberry Pi 3/4/5 and Rockchip RK3588 boards [src: file: workflows/bootc-debs-builder/kernel/modules/rk3588:3]. See [minimal § Architecture boundary](minimal.md#architecture-boundary). |
| Raspberry Pi `.img` | Optional arm64 disk-image stage (`run_img_rpi`, default off) [src: file: .github/workflows/pipeline.yml:44]. |
| QEMU/KVM test VM | Virtual disk the image is installed to and booted (UEFI) for runtime tests [src: file: workflows/tests.yml:2]. |
| Build container | Podman build with `--format docker`; no init, so services are blocked by `policy-rc.d` [src: file: README.md:62] [src: file: src/debianpreinstall/usr/sbin/policy-rc.d:3]. |

## External

| Term | Definition |
|------|------------|
| DaemonCores-CI | Shared repo holding the reusable `full-pipeline.yml@main` job graph [src: file: .github/workflows/pipeline.yml:71]. |
| DaemonCores-VE | Downstream project consuming the published `latest` image as its base [src: file: docs/architecture.md:12]; the reason the full image uses ifupdown2 [src: file: docs/justifications.md:31]. It is the maintainer's renamed fork of Proxmox VE: "Proxmox VE", "Proxmox bootc", "Proxmox-Atomic" and "DaemonCores VE" in code, comments or docs all mean this one project [src: user:pikatsuto:2026-10-18: disc-dc54c008] [src: file: workflows/bootc-debs-builder/bootcpostinstall/etc/kernel/postinst.d/zz-bootc-finalize:6]. |
| GHCR | GitHub Container Registry; publishes images and the buildenv [src: file: README.md:80] [src: file: workflows/env.yml:5]. |
| GitHub Pages APT repo | Signed APT repository served from `https://daemoncores.github.io/debian-bootc` [src: file: Containerfile.base:32] [src: file: README.md:85]. |
| GitHub wiki | Mirror of `docs/**` synced on push to `main` [src: file: .github/workflows/docs-wiki-sync.yml:5]. |
| cosign / Sigstore | Image signing with a per-repository key kept in repository secrets, keyless OIDC only as a fallback [src: file: docs/justifications.md:53]. |
| bootc-image-builder | Tool converting the installer image to an ISO via dracut live squashfs [src: file: Containerfile.iso:5]. |
| cage | Single-app Wayland compositor hosting the installer [src: file: Containerfile.iso:8]. |
| shim / Secure Boot | Signed EFI chain staged by `bootc-finalize`; GRUB EFI package signed with `SB_SIGNING_KEY`/`SB_SIGNING_CERT` [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:5] [src: file: README.md:82]. |
| U-Boot | arm64 bootloader tooling (`u-boot-tools`) used instead of GRUB by the `embedded` boot profile [src: file: Containerfile.minimal:13]. |
| Boot profile | `generic` (UEFI, Fedora GRUB: amd64, arm64 PCs, servers, VMs) or `embedded` (arm64 boards loading U-Boot); declared by `LABEL org.daemoncores.boot-profile`, generic when absent [src: file: Containerfile.minimal:101]. |
| Dependabot | Automated update PRs for actions [src: file: .github/dependabot.yml:1]. |

## Abbreviations

| Abbrev | Expansion |
|--------|-----------|
| BLS | Boot Loader Specification [src: file: workflows/bootc-debs-builder/preinstall/output/grub-efi-amd64-signed/DEBIAN/control:12] |
| OCI | Open Container Initiative (image format) [src: file: workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/control:12] |
| SB | Secure Boot (`SB_SIGNING_KEY`, `SB_SIGNING_CERT`) [src: file: README.md:82] |
| PAT | Personal Access Token (`PAT_PKG`, GHCR pull/publish) [src: file: README.md:80] |
| OIDC | OpenID Connect — GitHub Actions identity, used by cosign only for the keyless fallback [src: file: docs/justifications.md:57] |
| SBC | Single-board computer (arm64 targets) [src: file: Containerfile.minimal:97] |
| DTB | Device Tree Blob, board-specific on arm64 [src: file: docs/minimal.md:101] |
| GHCR | GitHub Container Registry [src: file: README.md:80] |
| ISO | Installer image file produced by `Containerfile.iso` [src: file: Containerfile.iso:5] |
| TUI | Text user interface (first-boot wizard) [src: file: workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:3] |
