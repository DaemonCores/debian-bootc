#!/usr/bin/env bash
# Kernel module signing setup, sourced by the kernel and kernel module build:
# blocks of packages.yml. Listed in their sources: so a change invalidates the
# cached debs.
#
# The kernel signs every module at modules_install time with
# CONFIG_MODULE_SIG_KEY (certs/signing_key.pem by default) and trusts the
# matching certificate through its built-in keyring. Giving the build the CI
# key at that default path makes the kernel image and the device module
# packages sign with ONE key, so every module verifies against the kernel.
#
# Inputs (environment): MODULE_SIGNING_ACTIVE ("yes" to sign), and when active
# MODULE_SIGNING_KEY and MODULE_SIGNING_CERT (PEM secrets of the CI).

#######################################
# Install the CI signing key in the current kernel source tree. Signing stays
# optional: without a configured key the full kernel build keeps the kernel's
# own behaviour (it generates a throw-away key), and only a modules-only tree,
# which cannot generate one, has the automatic signing turned off.
# Must run from the kernel source tree, before `make olddefconfig`.
# Arguments:
#   $1: "modules-only" for a tree that only builds modules, empty otherwise
# Globals:
#   MODULE_SIGNING_ACTIVE: read, "yes" when the modules must be signed
#   MODULE_SIGNING_KEY: read, private key (PEM), required when active
#   MODULE_SIGNING_CERT: read, certificate (PEM), required when active
# Returns:
#   Exits 1 when signing is active but the key or the certificate is empty.
#######################################
kernel_signing_setup() {
  if [ "${MODULE_SIGNING_ACTIVE:-}" != "yes" ]; then
    if [ "${1:-}" = "modules-only" ]; then
      # No key to sign with: the seeded .config still asks for
      # certs/signing_key.pem, which a modules-only tree does not have, and
      # modules_install aborts with an SSL "No such file or directory".
      scripts/config --disable MODULE_SIG_ALL
    fi
    return 0
  fi
  if [ -z "${MODULE_SIGNING_KEY:-}" ] || [ -z "${MODULE_SIGNING_CERT:-}" ]; then
    echo "ERROR: MODULE_SIGNING_ACTIVE=yes but MODULE_SIGNING_KEY or MODULE_SIGNING_CERT is empty" >&2
    exit 1
  fi
  mkdir -p certs
  # signing_key.pem carries the private key and the certificate: the kernel
  # extracts the certificate from it for the built-in keyring.
  (
    umask 077
    printf '%s\n%s\n' "${MODULE_SIGNING_KEY}" "${MODULE_SIGNING_CERT}" \
      > certs/signing_key.pem
  )
  printf '%s\n' "${MODULE_SIGNING_CERT}" > certs/signing_key.x509
  scripts/config --enable MODULE_SIG --enable MODULE_SIG_ALL \
    --set-str MODULE_SIG_KEY certs/signing_key.pem
}
