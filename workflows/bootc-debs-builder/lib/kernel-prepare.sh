#!/usr/bin/env bash
# Shared kernel-module build bootstrap, sourced by the build: blocks of
# linux-modules-arm, linux-modules-arm-device and linux-modules-x86_64 in
# packages.yml. Listed in each entry's sources: so a change invalidates the
# cached debs.
#
# Inputs (set by the caller): DEB_ARCH, SAVE_PWD (repository root).
# Outputs (globals): COMMON_DEB, BUILT_VER, KVER, SRCDIR, ARCH (kernel arch).
# BUILT_VER and KVER are consumed by the sourcing build: blocks.
# Leaves the shell inside the kernel source tree with .config seeded from the
# published linux-image-common deb; the caller merges its overlays and builds.

#######################################
# Prepare the kernel source tree and seed its .config.
# Globals:
#   DEB_ARCH: read, architecture of the matching linux-image-common deb
#   SAVE_PWD: read, repository root
#   COMMON_DEB: set
#   BUILT_VER: set
#   KVER: set
#   SRCDIR: set
#   ARCH: set, kernel architecture
# Returns:
#   Exits 1 when no matching linux-image-common deb is found.
#######################################
# shellcheck disable=SC2034  # BUILT_VER and KVER are used by the caller
kernel_prepare() {
  # The linux-image wave installed linux-image-common_<ver>_<arch>.deb
  # into the build container (via the deps install step). Derive the
  # exact version + kernel version string from it so the module source
  # download matches.
  # The workflow downloads ALL prior deb artifacts (both amd64 and arm64)
  # into /tmp/prior, so the bare linux-image-common_*.deb glob catches the
  # foreign-arch deb too and apt then fails with a Conflicts/Provides
  # collision (the common deb Conflicts with linux-image-amd64 AND
  # linux-image-arm64). Filter on the runner's DEB_ARCH so only the
  # matching-arch deb is selected.
  COMMON_DEB=$(find /tmp/prior -maxdepth 1 -name "linux-image-common_*_${DEB_ARCH}.deb" | head -1)
  test -n "${COMMON_DEB}" \
    || {
      echo "ERROR: linux-image-common deb not found in /tmp/prior" >&2
      exit 1
    }
  # Extract version + kernel version from the deb without installing it.
  BUILT_VER=$(dpkg-deb -f "${COMMON_DEB}" Version)
  KVER=$(dpkg-deb -f "${COMMON_DEB}" Package | sed 's/^daemoncores-kernel-//')

  # Install kernel build deps (build-essential + the kernel's own
  # build-deps). libncurses-dev/bc are required by the kconfig merge.
  apt-get update
  apt-get install -y --no-install-recommends \
    build-essential libncurses-dev bison flex libssl-dev libelf-dev bc \
    rsync libudev-dev elfutils dpkg-dev curl xz-utils

  # Download the kernel.org tarball of the version the common deb was built
  # from (the upstream part of BUILT_VER, before the package revision), so the
  # modules always match the kernel image whatever kernel.org released since.
  # shellcheck source=kernel-source.sh
  . "${SAVE_PWD}/workflows/bootc-debs-builder/lib/kernel-source.sh"
  kernel_fetch_source "${BUILT_VER%%-*}"
  # The modules build against the same patched tree as the image.
  # shellcheck source=kernel-patches.sh
  . "${SAVE_PWD}/workflows/bootc-debs-builder/lib/kernel-patches.sh"
  kernel_apply_patches \
    "${SAVE_PWD}/workflows/bootc-debs-builder/kernel/patches.yml" \
    kernel "${DEB_ARCH}" "${BUILT_VER%%-*}" "${SRCDIR}"

  apt-get install -y "${COMMON_DEB}"

  cd "${SRCDIR}" || return 1
  # Translate the Debian-style DEB_ARCH (amd64) to the kernel's arch dir
  # name (x86_64): the kernel Makefile includes arch/$(ARCH)/Makefile,
  # and arch/amd64/ does not exist, so an unmodified ARCH=amd64 fails
  # with "arch/amd64/Makefile: No such file or directory".
  # Export KERNEL_ARCH BEFORE any make invocation (olddefconfig,
  # modules, modules_install) — the runner's inherited
  # ARCH=amd64 would otherwise make `make olddefconfig` look for
  # arch/amd64/Makefile and fail on the first command. For ARM the
  # kernel arch dir is arm64, matching DEB_ARCH (no translation needed).
  KERNEL_ARCH="${DEB_ARCH}"
  [ "${KERNEL_ARCH}" = "amd64" ] && KERNEL_ARCH="x86_64"
  unset ARCH
  export ARCH="${KERNEL_ARCH}"

  # Start from the Debian config for this arch, then merge the base
  # config THEN the arm overlay (overlay wins on conflicts — last
  # merge wins).
  # Seed .config from the linux-image-common deb, which carries the .config
  # the kernel was built with at /usr/lib/linux-kernel-build/config. It has
  # to travel inside the deb: a cache hit restores only the .deb from the
  # published APT repo, so a file written beside it in /debs never reaches
  # this job. Starting from the same .config as the kernel build keeps
  # CONFIG_FUNCTION_TRACER and the other core settings identical, which is
  # what lets modpost resolve __fentry__.
  SEED_DIR=/tmp/linux-kernel-build-seed
  rm -rf "${SEED_DIR}"
  dpkg-deb -x "${COMMON_DEB}" "${SEED_DIR}"
  test -f "${SEED_DIR}/usr/lib/linux-kernel-build/config" \
    || {
      echo "ERROR: ${COMMON_DEB} carries no kernel config" >&2
      exit 1
    }
  cp "${SEED_DIR}/usr/lib/linux-kernel-build/config" .config
}
