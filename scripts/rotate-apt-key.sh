#!/bin/bash
#
# rotate-apt-key.sh - rotate the APT repository signing key from CI.
#
# Subcommands:
#   rotate           Generate a fresh key pair and store the private key as the
#                    APT_GPG_KEY secret.  The private key only ever travels
#                    through a pipe into `gh secret set`: it is never kept in a
#                    variable, a file outside the throw-away GNUPGHOME, a log
#                    or an artifact.  Prints the public fingerprint on stdout.
#   publish-hash FPR Wait until the published gpg.key carries the fingerprint
#                    FPR, then rewrite BOOTC_GPG_SHA256 in the Containerfiles
#                    with the SHA-256 of the file as served.
#
# Environment:
#   GH_TOKEN          token with secrets:write (PAT_SECRETS); for `rotate`
#   KEY_URL           published public key (default: the GitHub Pages URL)
#   ROOT_DIR          repository root (default: parent of this script)
#   WAIT_ATTEMPTS     polling attempts for publish-hash (default 60)
#   WAIT_SECONDS      delay between attempts (default 20)
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
KEY_URL="${KEY_URL:-https://daemoncores.github.io/debian-bootc/gpg.key}"
UID_NAME="debian-bootc APT repository"

#######################################
# Print an error to stderr and exit 1.
# Arguments:
#   $*: message
#######################################
die() {
  echo "rotate-apt-key: $*" >&2
  exit 1
}

#######################################
# Generate a key pair in a private GNUPGHOME and store the private key as the
# APT_GPG_KEY secret.  Nothing secret is printed.
# Globals:
#   UID_NAME
# Outputs:
#   The public key fingerprint on stdout.
#######################################
rotate() {
  local home fpr
  home=$(mktemp -d)
  # shellcheck disable=SC2064  # expand $home now, it is fixed for this call
  trap "rm -rf '${home}'" RETURN
  chmod 700 "${home}"
  export GNUPGHOME="${home}"
  gpg --batch --quiet --pinentry-mode loopback --passphrase '' \
    --quick-generate-key "${UID_NAME}" rsa4096 sign never 2>/dev/null
  fpr=$(gpg --batch --with-colons --list-keys \
    | awk -F: '/^fpr:/ {print $10; exit}')
  [[ -n "${fpr}" ]] || die "key generation produced no fingerprint"
  gpg --batch --quiet --pinentry-mode loopback --passphrase '' \
    --armor --export-secret-keys "${fpr}" 2>/dev/null \
    | gh secret set APT_GPG_KEY >/dev/null
  printf '%s\n' "${fpr}"
}

#######################################
# Print the fingerprint of the first key in a public key file.
# Arguments:
#   $1: path to an armored or binary public key
#######################################
fingerprint_of() {
  local home
  home=$(mktemp -d)
  GNUPGHOME="${home}" gpg --batch --with-colons --show-keys "$1" 2>/dev/null \
    | awk -F: '/^fpr:/ {print $10; exit}'
  rm -rf "${home}"
}

#######################################
# Wait for the published key to match FPR, then update the pinned hash.
# Globals:
#   ROOT_DIR, KEY_URL, WAIT_ATTEMPTS, WAIT_SECONDS
# Arguments:
#   $1: expected fingerprint
#######################################
publish_hash() {
  local want="$1" tmp i got digest file
  local attempts="${WAIT_ATTEMPTS:-60}" delay="${WAIT_SECONDS:-20}"
  [[ "${want}" =~ ^[0-9A-F]{40}$ ]] || die "expected a 40-hex fingerprint"
  tmp=$(mktemp)
  # shellcheck disable=SC2064
  trap "rm -f '${tmp}'" RETURN
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsSL "${KEY_URL}" -o "${tmp}" 2>/dev/null; then
      got=$(fingerprint_of "${tmp}")
      [[ "${got}" == "${want}" ]] && break
    fi
    got=""
    sleep "${delay}"
  done
  [[ "${got:-}" == "${want}" ]] \
    || die "published key never matched ${want} after ${attempts} attempts"
  digest=$(sha256sum "${tmp}" | awk '{print $1}')
  for file in "${ROOT_DIR}"/Containerfile "${ROOT_DIR}"/Containerfile.minimal; do
    grep -q '^ARG BOOTC_GPG_SHA256=' "${file}" \
      || die "no BOOTC_GPG_SHA256 in ${file}"
    sed -i "s/^ARG BOOTC_GPG_SHA256=.*/ARG BOOTC_GPG_SHA256=${digest}/" "${file}"
  done
  echo "BOOTC_GPG_SHA256=${digest}"
}

main() {
  set +x
  case "${1:-}" in
    rotate) rotate ;;
    publish-hash) publish_hash "${2:-}" ;;
    *) die "usage: $0 rotate | publish-hash FINGERPRINT" ;;
  esac
}

main "$@"
