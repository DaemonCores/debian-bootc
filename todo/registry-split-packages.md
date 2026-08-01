# Registry — split linux-image into per-device packages

Grep-markable point registry for splitting the monolithic linux-image entry
into separate YAML entries. Working ref (plan/todo); NEVER git-committed.

The disk is the territory — every STATUS flip is proven by a command.

<!-- BEGIN P01 -->
### P01 — Split monolithic linux-image into 6 separate YAML entries
- REQ (verbatim): "Split the monolithic linux-image entry into SEPARATE YAML
  entries: one entry 'linux-image' (builds the base kernel from kernel/config,
  produces linux-image-common_<ver>_<arch>.deb), then ONE ENTRY PER DEVICE:
  'linux-modules-rpi3' (depends on linux-image, builds from kernel/config +
  modules-kernel/rpi3), 'linux-modules-rpi4', 'linux-modules-rpi5',
  'linux-modules-rk3588', 'linux-modules-x86_64'. Each module entry is its own
  independent package with its own deps, sources, and build script."
- STATE (by command, 2026-08-01):
  - `grep -c 'name: linux' workflows/bootc-debs-builder/packages.yml` → 1
    (single monolithic `linux-image` entry with a Stage 2 loop over all
    modules-kernel/* fragments).
  - `ls modules-kernel/` → rk3588 rpi3 rpi4 rpi5 x86_64 (5 overlays).
  - Wave computation (DaemonCores-CI bootc-debs-builder.yml setup): deps dict
    → topological waves. linux-image has no deps → wave 0. Module entries
    with `deps: [linux-image]` → wave 1. Max 4 waves supported.
  - build-one-deb.yml: deps debs downloaded to /tmp/prior/, installed via
    apt-get. Build script runs in same container, so /tmp/prior persists.
  - build-deb.sh: DEB_GLOB defaults to `${PACKAGE}_*` when not specified.
    sources_hash() hashes all files listed in `sources:` → content-addressed
    cache skip.
- DECISION: Replace lines 41-225 (the monolithic entry) with 6 entries:
  1. `linux-image` — Stage 1 only (bindeb-pkg, produce
     linux-image-common_*.deb). sources: [../../kernel/config] only (NOT
     the overlays → changing an overlay does NOT invalidate the common
     image cache). deb-glob: "linux-image-common_*".
  2. `linux-modules-rpi3` — deps: [linux-image]. sources:
     [../../kernel/config, ../../modules-kernel/rpi3]. Build: install
     linux-image-common deb (via deps), derive BUILT_VER + KVER from it,
     apt-get source matching kernel, merge kernel/config + overlay, make
     modules, package as linux-modules-rpi3_<ver>_<arch>.deb. deb-glob
     defaults to linux-modules-rpi3_*. No arch gate (preserve current
     behavior — no regression).
  3-6. Same for rpi4, rpi5, rk3588, x86_64.
  Each module build script is identical except `DEVICE=<device>`. KVER is
  derived from the installed linux-image-common deb's Package field
  (e.g. "linux-image-6.8.0-1014-aws" → "6.8.0-1014-aws") so the module
  source download matches exactly. BUILT_VER from the deb's Version field.
  Depends: linux-image-common (= ${BUILT_VER}) — same as current monolithic
  build, preserving the exact same dependency semantics (zero regression).
- PLAN: edit workflows/bootc-debs-builder/packages.yml, replace lines 41-225.
- STATUS: ✅ DONE
  - Proof:
    - YAML parses (PyYAML in python:3-slim container): `docker run ... valpkgs2`
      → 14 entries, deps-valid: True, max wave: 2 (≤ 3).
    - `grep -cE '^  - name: ' workflows/bootc-debs-builder/packages.yml` → 14.
    - `grep -E '^  - name: linux' ...` → 6 entries: linux-image, linux-modules-rpi3,
      linux-modules-rpi4, linux-modules-rpi5, linux-modules-rk3588,
      linux-modules-x86_64.
    - linux-image: `deb-glob: "linux-image-common_*"`, sources: ONLY
      `../../kernel/config` (verified read lines 70-76).
    - Each module: `deps: [linux-image]`, sources:
      `[../../kernel/config, ../../modules-kernel/<device>]` (verified via
      grep -A6 for each).
    - Wave computation (replicated setup job): wave0 = [bootupd,
      firstboot-user-setup, grub-efi-amd64-signed, ifupdown2, libcomposefs,
      linux-image, systemd-timesyncd]; wave1 = [linux-modules-rk3588,
      linux-modules-rpi3, linux-modules-rpi4, linux-modules-rpi5,
      linux-modules-x86_64, ostree]; wave2 = [bootc]; wave3 = [].
    - shellcheck on 6 extracted kernel build scripts: 0 errors (warnings/infos
      only, all pre-existing patterns preserved from the original monolith
      for zero regression).
<!-- END P01 -->