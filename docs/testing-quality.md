# Testing & quality

How debian-bootc is validated: build-time checks run inside each `.deb` build script and each Containerfile, and runtime tests run over SSH on a QEMU/KVM boot of every built image before it is pushed. The job graph that runs these checks lives in the shared `DaemonCores/DaemonCores-CI` reusable workflow; this repo only declares the inputs [src: file: .github/workflows/pipeline.yml:3].

<!-- kronn:section name="build-checks" curated="ai" owner="audit" audit="2026-10-18" -->
## Build & quality checks

| Check | Where / command | Scope | Blocking |
|-------|-----------------|-------|----------|
| Package build (compile) | `build:` script per package in `workflows/bootc-debs-builder/packages.yml`, run in the `-buildenv` image [src: file: workflows/bootc-debs-builder/packages.yml:11] [src: file: workflows/env.yml:5] | 16 custom `.deb` packages [src: file: workflows/bootc-debs-builder/packages.yml:12] | Yes: the script runs under `set -euo pipefail` [src: file: workflows/bootc-debs-builder/packages.yml:20] |
| Per-package content checks | Inline `test -x` / `test -s` / `bash -n` assertions labelled `# Content check` [src: file: workflows/bootc-debs-builder/packages.yml:34] | 13 labelled checks (output deb non-empty, helpers executable, versions rewritten, shared objects built) | Yes: on failure CI keeps the last-good deb and opens an issue [src: file: workflows/bootc-debs-builder/packages.yml:1304] |
| Unit test (bootupd dpkg patch) | `cargo test --release --manifest-path /build/bootupd/Cargo.toml query_files_dpkg`, which must report at least 1 passed test [src: file: workflows/bootc-debs-builder/packages.yml:1307] | bootupd only | Yes [src: file: workflows/bootc-debs-builder/packages.yml:1312] |
| Signing key integrity | `sha256sum -c` against `BOOTC_GPG_SHA256` [src: file: Containerfile:80] [src: file: Containerfile.minimal:155] | Full and minimal images | Yes (image build fails) |
| Image build | `podman build --format docker ... -f Containerfile` [src: file: README.md:60] | Every root `Containerfile*` (architecture × update-variant matrix) [src: file: docs/architecture.md:54] | Yes |
| bootc validation (lint) | Runs in the shared image workflow after the build [src: file: docs/architecture.md:60]; a second `/usr/lib/modules/<kver>/` fails it [src: file: Containerfile:21] | Every image | Yes |
| Runtime boot tests | `workflows/tests.yml`, run over SSH on a QEMU/KVM boot of the installed image [src: file: workflows/tests.yml:1] | 35 tests, see [Test suites](#test-suites) | Yes: a failing test blocks the push [src: file: workflows/tests.yml:3] |
| Test manifest integrity | The harness refuses to run if any test lacks `diag` [src: file: workflows/tests.yml:11] | `workflows/tests.yml` | Yes |
| Format / lint of shell, YAML, Python | None configured: no shellcheck, hadolint, yamllint, pre-commit or Python linter config in the repo | — | — |
<!-- kronn:section:end -->

<!-- kronn:section name="test-infrastructure" curated="ai" owner="audit" audit="2026-10-18" -->
## Test infrastructure

| Layer | Runner | Config file | Runtime / version |
|-------|--------|-------------|-------------------|
| Runtime image tests | DaemonCores-CI image workflow harness: `bootc install` to a virtual disk, QEMU/KVM + UEFI boot, then SSH [src: file: docs/architecture.md:61] | `workflows/tests.yml` (`boot_timeout: 900`, `reboot_timeout: 300`) [src: file: workflows/tests.yml:24] | Debian 13 Trixie image under test [src: file: Containerfile:5]; arches amd64 and arm64 [src: file: workflows/tests.yml:13] |
| Rust unit test (bootupd) | `cargo test` inside the package build [src: file: workflows/bootc-debs-builder/packages.yml:1307] | `/build/bootupd/Cargo.toml` (upstream source, not in repo) | Rust via rustup, minimal profile, unpinned [src: file: workflows/env.yml:101] |
| Build-time content checks | Bash, `set -euo pipefail` [src: file: workflows/bootc-debs-builder/packages.yml:20] | `workflows/bootc-debs-builder/packages.yml` | `-buildenv` image built from `workflows/env.yml` [src: file: workflows/env.yml:5] |
| Python | No test runner (no pytest/unittest config) | — | Python 3, unpinned [src: file: scripts/gen-recipe.py:1] |

Test-entry fields: `name`, `run` (pass on exit 0), `expect` (optional output match), `diag` (required), `arch` (`amd64`/`arm64`), `variant` (`main`/`minimal`). A gated test that does not match the current target reports SKIP, not FAIL [src: file: workflows/tests.yml:5-22].
<!-- kronn:section:end -->

<!-- kronn:section name="test-suites" curated="ai" owner="audit" audit="2026-10-18" -->
## Test suites

All runtime suites are section groups in `workflows/tests.yml` (42 tests, each with a `diag`).

| Suite (section in `workflows/tests.yml`) | Tests | Gating |
|-------|-------|--------|
| bootc / ostree / immutability / service stability [src: file: workflows/tests.yml:30] | 10 | 8 all targets; logind not-masked and FailureAction=none: all targets |
| bootloader / secure boot [src: file: workflows/tests.yml:72] | 6 | 5 × `arch: amd64` (bootupd, GRUB, shim, SB cert); 1 × `arch: arm64` (u-boot-tools) [src: file: workflows/tests.yml:105] |
| kernel / initramfs / dracut [src: file: workflows/tests.yml:112] | 4 | all targets |
| filesystems (btrfs) [src: file: workflows/tests.yml:135] | 2 | `arch: amd64` |
| podman [src: file: workflows/tests.yml:154] | 2 | `arch: amd64` |
| networking / repacked packages [src: file: workflows/tests.yml:169] | 9 | ifupdown2 / autoconf / IP: `variant: main`; sshd: `arch: amd64`; SSH host keys: all targets; networkd active / IP: `variant: minimal` |
| first-boot tooling [src: file: workflows/tests.yml:198] | 2 | firstboot wizard `variant: main` |
| rollback preparation, pre-reboot [src: file: workflows/tests.yml:211] | 3 | all targets |
| post-rollback verification, after reboot [src: file: workflows/tests.yml:233] | 4 | all targets |

Build-time suites: 13 labelled content checks across the `packages.yml` build scripts, plus one `cargo test` (bootupd `query_files_dpkg`, at least 1 passing test) [src: file: workflows/bootc-debs-builder/packages.yml:1307].
<!-- kronn:section:end -->

<!-- kronn:section name="coverage" curated="ai" owner="audit" audit="2026-10-18" -->
## Coverage

- Current status: no code-coverage tooling. Coverage is behavioural: 42 runtime assertions on the booted image [src: file: workflows/tests.yml:29] and build-time content checks per package [src: file: workflows/bootc-debs-builder/packages.yml:34].
- Target: no numeric target is defined. The test policy requires a runtime test with a `diag` for every change to boot, filesystem, networking or service behaviour [src: file: docs/AGENTS.md:15].
<!-- kronn:section:end -->

<!-- kronn:section name="untested" curated="ai" owner="audit" audit="2026-10-18" -->
## Untested components

- `scripts/gen-recipe.py`: no unit tests [src: file: scripts/gen-recipe.py:1].
- Installer ISOs (`Containerfile.iso`, `bootc-installer`): `workflows/tests.yml` has no installer/ISO test; the build only checks that the launcher and GResource bundle exist [src: file: workflows/bootc-debs-builder/packages.yml:1683].
- `fisherman`: no runtime test in `workflows/tests.yml` [src: file: workflows/bootc-debs-builder/packages.yml:1541].
- Minimal image autoupdate behaviour (`/usr/lib/bootc/autoupdate`, `AUTOUPDATE` arg): no runtime test [src: file: Containerfile.minimal:158].
- arm64 image: only the u-boot-tools test is arm64-specific [src: file: workflows/tests.yml:105]; bootloader, btrfs, podman and sshd tests are amd64-only. The 5 networking tests added in the stabilization pass are split: SSH host keys is all-targets; ifupdown2-autoconf, main-IP are variant:main; networkd-active, minimal-IP are variant:minimal.
- Raspberry Pi `.img` artifacts (`run_img_rpi`): no boot test in this repo [src: file: .github/workflows/pipeline.yml:44].
- Linux kernel and module `.deb`s: build-time existence checks only (`test -s` on the output deb) [src: file: workflows/bootc-debs-builder/packages.yml:412]; runtime checks cover only the modules tree and btrfs loading [src: file: workflows/tests.yml:113].
<!-- kronn:section:end -->

<!-- kronn:section name="smoke-checks" curated="ai" owner="audit" audit="2026-10-18" -->
## Smoke checks (pre-commit)

```bash
# 1. Every runtime test has a diag (the harness rejects the manifest otherwise); the two counts must match
grep -c '^  - name:' workflows/tests.yml; grep -c '^    diag:' workflows/tests.yml

# 2. Syntax-check the installer recipe generator
python3 -m py_compile scripts/gen-recipe.py

# 3. Local full-image build (amd64 host)
podman build --format docker --build-arg PRODUCT_NAME="debian bootc" -f Containerfile -t debian-bootc:local .

# 4. bootc lint on the local image
podman run --rm debian-bootc:local bootc container lint

# 5. Package build inputs changed? Confirm they are declared under that package's sources/env
git diff --name-only -- workflows/bootc-debs-builder/
```

Sources: the build command is from [src: file: README.md:60]; the `diag` rule is from [src: file: workflows/tests.yml:9]; the `sources`/`env` hashing rule is from [src: file: workflows/bootc-debs-builder/packages.yml:7]. Command 4 is a local equivalent of the CI bootc validation step [src: inferred: docs/architecture.md:60].
<!-- kronn:section:end -->
