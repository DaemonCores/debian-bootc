---
name: td-20261018-full-image-install-recommends
description: Main Containerfile's package install omits `--no-install-recommends`, unlike every other apt install in the repo.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Docker audit 0.8.2
      note: re-confirmed by Docker audit 0.8.2 at Containerfile:101 (layer hygiene); ID reused
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-full-image-install-recommends

- **Area**: Infra
- **Category**: docker
- **Severity**: Low
- **Status**: Fixed (not built; resolution checked with apt-get -s)
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
Phase 3 of `Containerfile` runs `apt install -y` for ~50 packages without `--no-install-recommends`. Phases 1/3.1 of the same file, `Containerfile.minimal` and `Containerfile.iso` all pass the flag. Apt list cleanup is handled globally by `99-apt-clean`, so that part of the baseline is satisfied.

## Impact
Recommends pulled in by ~50 packages add unreviewed packages and size to the OS image, and to every ostree update delta. Users cannot tell whether the difference from the minimal image is intentional.

## Where (pointers)
- `Containerfile:101` — `apt install -y` without --no-install-recommends
- `Containerfile:58` — same file uses the flag in Phase 1
- `Containerfile.minimal:183` — minimal image uses the flag
- `src/debianpreinstall/etc/apt/apt.conf.d/99-apt-clean:1` — lists cleanup via DPkg::Post-Invoke

## Suggested direction
Add `--no-install-recommends` and list any genuinely wanted recommends explicitly. If pulling recommends is intended for the 'full' flavour, say so in a comment and in docs/justifications.md.

## Next step
`create ticket`

## Resolution
Phase 3 of `Containerfile` now passes `--no-install-recommends` and lists the recommends the OS needs. Simulated with `apt-get -s` against trixie plus the debian-bootc repo (amd64): 425 packages before, 353 after, and the list resolves without error. Dropped: exim4, cron, buildah, criu, logrotate and other unreviewed packages. Kept explicitly: parted/dosfstools/fdisk (bootc install), uidmap/passt/aardvark-dns/nftables/catatonit/containers-storage/fuse-overlayfs (rootless podman), cryptsetup/systemd-cryptsetup/kpartx/mdadm/zstd (dracut), the firmware-* recommends, and console/ssh helpers. No image was built or booted; the CI boot test is the check.

Both architectures were simulated (arm64 with `APT::Architecture "arm64"`, the arm64 build args `BOOT_PKG=u-boot-tools` and no microcode, and the arm64 kernel modules). The package lists are read from the `Containerfile` itself, so they match what a build installs. After the change amd64 installs 354 packages and arm64 359, both without resolver errors. The architecture specific recommends are installed in the per-arch block at the end of the install `RUN`:

- amd64: `firmware-intel-graphics`, `firmware-intel-misc`, `firmware-nvidia-graphics` (x86 GPU and platform firmware, previously in the global list).
- arm64: `efibootmgr` (recommended by the GRUB EFI packages that `bootupd` pre-depends on), `libubootenv-tool` (`fw_printenv`/`fw_setenv`) and `device-tree-compiler`, both recommended by `u-boot-tools`.

The remaining dropped recommends are the same on both architectures (compilers and binutils, buildah, criu, X11 client libraries, logrotate, slirp4netns, glib introspection, language data). Still not built: the arm64 image has not been built or booted either.
