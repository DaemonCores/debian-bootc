# Debug & operations

Operational commands and troubleshooting for debian-bootc. The repo has no Makefile, `package.json`, justfile or compose file: images are built with Podman from the root `Containerfile*` files, and builds, tests and publication run in the shared `DaemonCores/DaemonCores-CI` reusable workflow that `.github/workflows/pipeline.yml` calls [src: file: .github/workflows/pipeline.yml:71].

<!-- kronn:section name="common-commands" curated="ai" owner="audit" audit="2026-10-18" -->
## Common commands

| Action | Command |
|--------|---------|
| Build full image (amd64 host) | `podman build --format docker --build-arg PRODUCT_NAME="debian bootc" -f Containerfile -t debian-bootc:local .` [src: file: README.md:62] |
| Build minimal image (amd64) | `podman build --format docker --build-arg ARCH=amd64 --build-arg BOOT_PKG=grub-efi-amd64-signed --build-arg KERNEL_VARIANT=minimal -f Containerfile.minimal -t debian-bootc:minimal-amd64 .` [src: file: docs/minimal.md:73] |
| Lint a built image (local equivalent of CI bootc validation) | `podman run --rm debian-bootc:local bootc container lint` [src: file: docs/testing-quality.md:92] |
| Inspect a built image (shell, no boot) | `podman run --rm -it debian-bootc:local bash` [src: inferred: standard podman usage; the image is Debian-based, `Containerfile:5`] |
| Start / stop | N/A — no long-running service in this repo. The image is booted only by the CI harness (`bootc install` to a virtual disk, QEMU/KVM + UEFI, SSH) [src: file: workflows/tests.yml:1] |
| Test (runtime) | Runs in CI on every image build from `workflows/tests.yml`; no local runner script in the repo [src: file: workflows/tests.yml:3] |
| Test (pre-commit smoke) | `grep -c '^  - name:' workflows/tests.yml; grep -c '^    diag:' workflows/tests.yml` (counts must match) and `python3 -m py_compile scripts/gen-recipe.py` [src: file: docs/testing-quality.md:79] |
| Deploy (push to `main`) | Triggers the full pipeline; untouched stages auto-skip; `docs/**` / `**.md`-only pushes do not trigger it [src: file: .github/workflows/pipeline.yml:18] |
| Deploy (manual, stage selection) | `gh workflow run pipeline.yml -f run_debs=true -f run_image=true -f run_iso=true` (also `rebuild_env`, `run_img_rpi`, `sign_modules`) [src: file: .github/workflows/pipeline.yml:26] |
| Rebuild package toolchain image | `gh workflow run pipeline.yml -f rebuild_env=true` — needed once to seed it or after editing `workflows/env.yml` [src: file: .github/workflows/pipeline.yml:29] |
| Logs (CI) | `gh run list --workflow pipeline.yml` then `gh run view <run-id> --log-failed`; failing runtime tests print their `diag` output [src: file: workflows/tests.yml:9] |
| Sync docs to wiki | Automatic on push to `docs/**` on `main`, or `gh workflow run docs-wiki-sync.yml` [src: file: .github/workflows/docs-wiki-sync.yml:3] |
<!-- kronn:section:end -->

<!-- kronn:section name="docker-services" curated="ai" owner="audit" audit="2026-10-18" -->
## Docker services

N/A — no compose file and no long-running containers. The containers below are build artefacts; none expose ports.

| Image | Port | Role | Health check |
|-------|------|------|--------------|
| `ghcr.io/<owner>/<repo>-buildenv` | — | Toolchain for `.deb` package builds [src: file: workflows/env.yml:5] | Package `build:` scripts under `set -euo pipefail` + content checks [src: file: workflows/bootc-debs-builder/packages.yml:20] |
| Full image (`Containerfile`) | — | Debian 13 bootc OS image [src: file: Containerfile:5] | bootc lint + runtime tests in `workflows/tests.yml` [src: file: workflows/tests.yml:1] |
| Minimal image (`Containerfile.minimal`) | — | Reduced multi-arch image, one image per tag [src: file: Containerfile.minimal:111] | Same as full image; `variant: main` tests report SKIP [src: file: workflows/tests.yml:18] |
| Installer ISO (`Containerfile.iso`) | — | Installer media [src: file: Containerfile.iso:28] | No runtime test [src: file: docs/testing-quality.md:66] |
<!-- kronn:section:end -->

<!-- kronn:section name="troubleshooting" curated="ai" owner="audit" audit="2026-10-18" -->
## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Image build fails on `apt update` with a hash mismatch | CDN race on the GitHub Pages APT repo after a publish [src: commit: b24d611] | Already retried 5× with 30 s sleeps [src: file: Containerfile:98]; rerun the job if all retries fail |
| Image build fails at signing-key verification | The key served by the APT site does not match the digest passed as `BOOTC_GPG_SHA256` (for a local build, the Containerfile default is the upstream key's digest) [src: file: Containerfile:46] | In CI the `apt_key` job derives the digest from the `APT_GPG_KEY` secret and waits for the published `gpg.key` to carry the secret's fingerprint; if it times out, the Pages deployment is stale or the secret and the published key diverged: rerun the `Rotate APT signing key` workflow (thin caller [src: file: .github/workflows/rotate-apt-key.yml:1] of the shared `DaemonCores-CI/.github/workflows/rotate-apt-key.yml`, quarterly and on demand), which generates a fresh key, stores it in `APT_GPG_KEY` and restarts the pipeline. For a local build pass `--build-arg BOOTC_GPG_SHA256=$(wget -qO- <url>/gpg.key \| sha256sum \| cut -d' ' -f1) --build-arg BOOTC_APT_URL=<url>`. The private key only goes through a pipe into `gh secret set`; it is never logged nor uploaded. Rotation does not affect installed hosts: they update through the bootc container image, not through APT [src: user:pikatsuto:2026-10-18: disc-dc54c008 apt-key-rotation-owner] |
| bootc lint fails: two `/usr/lib/modules/<kver>/` dirs | Debian kernel (`linux-image-amd64/arm64`) or `linux-headers-*` co-installed with the custom kernel [src: file: Containerfile.minimal:169] | Install only one kernel per image: Debian's in the standard image, `linux-image-${KERNEL_VARIANT}-${ARCH}` in the minimal image |
| Runtime tests time out waiting for SSH (VM gets no IP) | Main image: missing `/etc/network/interfaces` for ifupdown2 (autoconf marker absent, DHCP never probed); minimal image: `systemd-networkd.service` not enabled (binary ships with the `systemd` package on Trixie — no separate package to install) [src: commit: e9ff026] | Keep the autoconf marker in `src/debianpostinstall/etc/network/interfaces` [src: file: src/debianpostinstall/etc/network/interfaces:1]; `systemctl enable systemd-networkd.service` in Containerfile.minimal Phase 3 is the minimal fix [src: file: Containerfile.minimal:231] |
| VM reboots in a loop during boot tests | Custom kernel exposes no DRM device; `systemd-logind` hits its start limit and `FailureAction=reboot` fires [src: commit: 3524e8e] | `FailureAction=none` drop-in in `src/{debian,minimal}postinstall/etc/systemd/system/systemd-logind.service.d/headless.conf` [src: file: src/debianpostinstall/etc/systemd/system/systemd-logind.service.d/headless.conf:2] |
| Stale `.deb` reused after changing a package build input | Only paths/env declared in the package's `sources`/`env` are hashed for the content cache [src: file: workflows/bootc-debs-builder/packages.yml:7] | Declare the new input under that package in `packages.yml` |
<!-- kronn:section:end -->
