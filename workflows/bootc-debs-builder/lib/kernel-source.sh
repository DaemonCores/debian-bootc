#!/usr/bin/env bash
# Shared kernel source download, sourced by the build: blocks of every kernel
# entry in packages.yml (and by lib/kernel-prepare.sh). Listed in each entry's
# sources: so a change invalidates the cached debs.
#
# The kernel is the kernel.org tarball, never a distribution source package.

KERNEL_CDN="${KERNEL_CDN:-https://cdn.kernel.org/pub/linux/kernel}"

#######################################
# Download, verify and extract the kernel.org tarball of one release.
# Globals:
#   KERNEL_CDN: read, root of the kernel.org archive
#   SRCDIR: set, the extracted source tree
# Arguments:
#   $1 - kernel version, e.g. 7.3 or 7.2.11
#   $2 - optional sha256 of the tarball; read from sha256sums.asc when empty
# Returns:
#   Exits 1 when the download fails or the checksum does not match.
#######################################
kernel_fetch_source() {
  local version="$1" want="${2:-}" dir tarball got
  dir="${KERNEL_CDN}/v${version%%.*}.x"
  tarball="linux-${version}.tar.xz"
  cd /tmp || return 1
  curl --retry 3 -fsSLO "${dir}/${tarball}" \
    || {
      echo "ERROR: cannot download ${dir}/${tarball}" >&2
      exit 1
    }
  if [[ -z "${want}" ]]; then
    want=$(curl --retry 3 -fsSL "${dir}/sha256sums.asc" \
      | awk -v n="${tarball}" '$2 == n { print $1 }')
  fi
  got=$(sha256sum "${tarball}" | cut -d' ' -f1)
  [[ "${want}" =~ ^[0-9a-f]{64}$ && "${got}" == "${want}" ]] \
    || {
      echo "ERROR: sha256 of ${tarball} is ${got}, expected '${want}'" >&2
      exit 1
    }
  rm -rf "/tmp/linux-${version}"
  tar -xf "${tarball}"
  rm -f "${tarball}"
  SRCDIR="/tmp/linux-${version}"
  test -d "${SRCDIR}" \
    || {
      echo "ERROR: ${tarball} did not extract to ${SRCDIR}" >&2
      exit 1
    }
}
