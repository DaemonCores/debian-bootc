# Repo map

## Stack overview

debian-bootc builds Debian 13 (Trixie) bootc/OSTree OS images from root-level Containerfiles with Podman: `Containerfile` (full image) and `Containerfile.minimal` (reduced image) both start `FROM` the shared `Containerfile.base`, itself `FROM debian:trixie` [src: file: Containerfile.base:10], and `Containerfile.iso` builds an installer ISO on top of the published `debian-bootc` image [src: file: Containerfile.iso:28]. The images install custom `.deb` packages (bootc, ostree, libcomposefs, bootupd, signed GRUB, kernel image and module packages, ifupdown2/systemd-timesyncd repacks, first-boot setup) declared in `workflows/bootc-debs-builder/packages.yml` [src: file: workflows/bootc-debs-builder/packages.yml:1] and built inside a build-environment image described by `workflows/env.yml` [src: file: workflows/env.yml:1]. CI is a thin caller (`.github/workflows/pipeline.yml`) of the shared `DaemonCores/DaemonCores-CI` `full-pipeline.yml`, which owns the job graph (plan, env, debs, image, iso) [src: file: .github/workflows/pipeline.yml:3] [src: file: .github/workflows/pipeline.yml:71]; each built image is installed to a virtual disk, booted under QEMU/KVM and tested over SSH from `workflows/tests.yml` before it is pushed [src: file: workflows/tests.yml:2]. There is no application code; the repository is Containerfiles, YAML manifests, shell overlays, kernel config fragments and one Python helper (`scripts/gen-recipe.py`) [src: file: scripts/gen-recipe.py:1].

## Key folders

```text
.
├── Containerfile                  # full image (debian:trixie → bootc stack, kernel, SSH, Podman, ifupdown2)
├── Containerfile.minimal          # reduced multi-arch image, see docs/minimal.md
├── Containerfile.iso              # installer ISO, FROM ghcr.io/daemoncores/debian-bootc:latest_${ARCH}
├── config.yml                     # distribution settings: module signing default (nosign|sign|both)
├── .github/
│   ├── workflows/
│   │   ├── pipeline.yml           # triggers (push main, dispatch, monthly cron) → DaemonCores-CI full-pipeline.yml
│   │   └── docs-wiki-sync.yml     # syncs docs/** to the GitHub wiki via DaemonCores-CI
│   ├── ISSUE_TEMPLATE/            # bug_report / feature_request forms
│   └── dependabot.yml
├── src/                           # filesystem overlays COPY'd into images (paths mirror /)
│   ├── debianpreinstall/          # before package install (apt config, usr/sbin) — full + minimal
│   ├── bootcpreinstall/           # bootc APT repo sources — full + minimal
│   ├── debianpostinstall/         # full image only: issue, motd, hostname, hosts, network, systemd
│   ├── minimalpostinstall/        # minimal image only: systemd units/drop-ins
│   └── buildisopreinstall/        # ISO only: bootc-installer recipe.json, polkit, containers, getty, var/home
├── workflows/
│   ├── bootc-debs-builder/        # custom .deb build inputs
│   │   ├── packages.yml           # package manifest: name, upstream, deps (waves), sources (hashed), env, build script
│   │   ├── preinstall/            # build-env overlay + output/<pkg>/DEBIAN/{control,postinst,triggers}
│   │   ├── patches/               # upstream patches (e.g. bootupd dpkg patch)
│   │   ├── bootcpostinstall/      # files shipped in the bootc deb (bootc-finalize, dracut conf, tmpfiles)
│   │   ├── ostreepostinstall/     # ostree prepare-root.conf
│   │   ├── firstbootpostinstall/  # firstboot-user-setup script + getty@tty1 drop-in
│   │   ├── ifupdown2postinstall/  # bootc-aware ifupdown2 repack (interfaces, autoconf, domain-set)
│   │   ├── timesyncpostinstall/   # bootc-aware systemd-timesyncd repack
│   │   └── kernel/                # inputs of the linux-* packages
│   │       ├── config             # base kernel config fragment shared by all devices (linux-image-common)
│   │       ├── pages/             # arm64 page-size fragments: 4k (Pi 3/4) and 16k (Pi 5, RK3588)
│   │       └── modules/           # per-target overlays: x86_64 and arm are merged into the kernel build, rpi3/rpi4/rpi5/rk3588 into the device modules packages
│   ├── env.yml                    # buildah recipe for the <repo>-buildenv image
│   └── tests.yml                  # runtime boot tests (name, diag, arch/variant gating)
├── scripts/
│   └── gen-recipe.py              # regenerates bootc-installer recipe.json from Containerfile* at ISO build
├── assets/installer/              # installer SVG artwork
└── docs/                          # agent/human docs, routed from docs/AGENTS.md (see docs/Home.md)
```

Sources: [src: file: Containerfile.base:52] [src: file: Containerfile:65] [src: file: Containerfile:106] [src: file: Containerfile.base:25] [src: file: Containerfile.minimal:180] [src: file: Containerfile.iso:53] [src: file: workflows/bootc-debs-builder/packages.yml:3] [src: file: workflows/bootc-debs-builder/kernel/config:3] [src: file: workflows/bootc-debs-builder/kernel/modules/rpi5:3] [src: file: config.yml:2] [src: file: .github/workflows/docs-wiki-sync.yml:11].

Local, untracked tool state (not part of the project): `lancedb/` (empty index directories) and `.kronn/` (ignored via the user's global gitignore).

## Entrypoints

| File | Role |
| --- | --- |
| `Containerfile` | Full image build: base, APT repo + GPG digest check, package install, OSTree layout [src: file: Containerfile.base:10] |
| `Containerfile.minimal` | Minimal image build contract [src: file: Containerfile.base:10] |
| `Containerfile.iso` | Installer ISO image; runs `gen-recipe.py` [src: file: Containerfile.iso:58] |
| `workflows/bootc-debs-builder/packages.yml` | Every custom `.deb`: deps, hashed sources/env, verbatim build script [src: file: workflows/bootc-debs-builder/packages.yml:1] |
| `workflows/tests.yml` | Runtime tests run over SSH on the QEMU-booted image; every test needs a `diag` [src: file: workflows/tests.yml:9] |
| `.github/workflows/pipeline.yml` | CI triggers, dispatch inputs and concurrency; delegates to DaemonCores-CI [src: file: .github/workflows/pipeline.yml:17] |
| `workflows/bootc-debs-builder/kernel/config` | Base kernel configuration for the common kernel image [src: file: workflows/bootc-debs-builder/kernel/config:1] |

## Auto-generated files

- `src/buildisopreinstall/etc/bootc-installer/recipe.json` — committed seed, but overwritten at ISO build time by `scripts/gen-recipe.py` from the `Containerfile*` list; add image variants by adding a Containerfile, not by editing this file [src: file: Containerfile.iso:58].
- `docs/.kronn-citation-originals/` — Kronn tool backups, not project content.
- Build outputs ignored by git: `*.iso`, `out/`, `tmp/`, `Archive.zip` [src: file: .gitignore:1].
- Not in the repo but produced by CI: the `.deb` packages and signed APT repository (GitHub Pages) and the OCI images on GHCR [src: file: docs/architecture.md:39].
