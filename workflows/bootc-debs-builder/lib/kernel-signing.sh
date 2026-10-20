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
# When signing is active the kernel also ENFORCES it: unsigned or foreign
# modules are refused, and the secondary and machine keyrings are built in so
# a certificate enrolled through MOK (see mok-stage) is trusted for modules.
# When signing is inactive nothing is signed and nothing is forced.
#
# Inputs (environment): MODULE_SIGNING_ACTIVE ("yes" to sign), and when active
# MODULE_SIGNING_KEY and MODULE_SIGNING_CERT (PEM secrets of the CI).

#######################################
# Install the CI signing key in the current kernel source tree, or turn the
# automatic signing off when no key is configured.
# Must run from the kernel source tree, before `make olddefconfig`.
# Globals:
#   MODULE_SIGNING_ACTIVE: read, "yes" when the modules must be signed
#   MODULE_SIGNING_KEY: read, private key (PEM), required when active
#   MODULE_SIGNING_CERT: read, certificate (PEM), required when active
# Returns:
#   Exits 1 when signing is active but the key or the certificate is empty.
#######################################
kernel_signing_setup() {
  if [ "${MODULE_SIGNING_ACTIVE:-}" != "yes" ]; then
    # No key to sign with: without this the seeded .config still asks for
    # certs/signing_key.pem, which a modules-only tree does not have, and
    # modules_install aborts with an SSL "No such file or directory".
    scripts/config --disable MODULE_SIG_ALL
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
      >certs/signing_key.pem
  )
  printf '%s\n' "${MODULE_SIGNING_CERT}" >certs/signing_key.x509
  scripts/config --enable MODULE_SIG --enable MODULE_SIG_ALL \
    --set-str MODULE_SIG_KEY certs/signing_key.pem
  # Enforcement and the keyrings a MOK-enrolled certificate lands in.
  # LOAD_UEFI_KEYS follows from INTEGRITY_PLATFORM_KEYRING on EFI.
  local opt
  for opt in "${KERNEL_SIGNING_FORCED[@]}"; do
    scripts/config --enable "${opt}"
  done
}

# Options forced when signing is active, checked after `make olddefconfig`.
KERNEL_SIGNING_FORCED=(
  MODULE_SIG MODULE_SIG_ALL MODULE_SIG_FORCE
  SYSTEM_BLACKLIST_KEYRING SECONDARY_TRUSTED_KEYRING
  INTEGRITY INTEGRITY_SIGNATURE INTEGRITY_ASYMMETRIC_KEYS
  INTEGRITY_PLATFORM_KEYRING INTEGRITY_MACHINE_KEYRING
)

#######################################
# Fail when `make olddefconfig` dropped an option forced by
# kernel_signing_setup (an unmet dependency would silently weaken the
# enforcement). Does nothing when signing is inactive.
# Must run from the kernel source tree, after `make olddefconfig`.
# Globals:
#   MODULE_SIGNING_ACTIVE: read
#   KERNEL_SIGNING_FORCED: read
# Returns:
#   Exits 1 when a forced option is not set to y in .config.
#######################################
kernel_signing_verify() {
  [ "${MODULE_SIGNING_ACTIVE:-}" = "yes" ] || return 0
  local opt missing=0
  for opt in "${KERNEL_SIGNING_FORCED[@]}"; do
    if ! grep -qx "CONFIG_${opt}=y" .config; then
      echo "ERROR: CONFIG_${opt} was dropped by olddefconfig while signing is active" >&2
      missing=1
    fi
  done
  [ "${missing}" -eq 0 ] || exit 1
}
