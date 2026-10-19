#!/bin/bash
#
# e2e-local.sh - run the CI boot test (workflows/tests.yml) against a local
# image, using the same harness as CI (DaemonCores-CI/image-test/image-test.sh).
#
# Usage: scripts/e2e-local.sh IMAGE [ARCH]
#   IMAGE  image already present in local podman storage (e.g. localhost/x:minimal)
#   ARCH   amd64 (default) or arm64
#
# Environment:
#   CI_REPO  path to a DaemonCores-CI checkout (default: ../DaemonCores-CI)
#
# The harness installs QEMU with apt-get and needs sudo, so this runs on a
# Debian/Ubuntu host with /dev/kvm. It is not usable inside the dev container.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly ROOT
readonly CI_REPO="${CI_REPO:-${ROOT}/../DaemonCores-CI}"

#######################################
# Print an error to stderr and exit 1.
# Arguments:
#   $* - message
#######################################
die() {
  echo "e2e-local: $*" >&2
  exit 1
}

#######################################
# Check that every prerequisite is in place before paying for a boot.
# Arguments:
#   $1 - image ref
#   $2 - architecture
#######################################
preflight() {
  local image="$1" arch="$2" tool
  [[ "${arch}" == amd64 || "${arch}" == arm64 ]] || die "ARCH must be amd64 or arm64"
  for tool in podman sudo apt-get; do
    command -v "${tool}" >/dev/null || die "missing required tool: ${tool}"
  done
  [[ -r "${CI_REPO}/image-test/image-test.sh" ]] \
    || die "harness not found, set CI_REPO (tried ${CI_REPO})"
  if [[ "${arch}" == amd64 && ! -e /dev/kvm ]]; then
    die "/dev/kvm is absent: the amd64 boot test needs hardware virtualization"
  fi
  podman image exists "${image}" || die "image not in local podman storage: ${image}"
}

#######################################
# Run the image boot tests against a local podman image.
# Globals:
#   ROOT
#   CI_REPO
# Arguments:
#   $1: image reference in local podman storage
#   $2: architecture, amd64 (default) or arm64
# Returns:
#   Exits 1 on a usage error or a failed preflight, else the harness status.
#######################################
main() {
  local image="${1:-}" arch="${2:-amd64}"
  [[ -n "${image}" ]] || die "usage: $0 IMAGE [ARCH]"
  preflight "${image}" "${arch}"
  IMAGE="${image}" ARCH="${arch}" TESTS_FILE="${ROOT}/workflows/tests.yml" \
    bash "${CI_REPO}/image-test/image-test.sh"
}

main "$@"
