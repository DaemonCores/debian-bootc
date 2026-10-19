#!/usr/bin/env bash
# Shared kernel patch application, sourced by the build: blocks of the kernel
# entries in packages.yml. Listed in each entry's sources: together with
# kernel/patches.yml so a change to either invalidates the cached debs.
#
# The patches are downloaded from their official upstream URL at build time and
# applied to the source tree in manifest order: common first, then the
# architecture. Nothing is tolerated: a patch that cannot be downloaded or does
# not apply makes the build fail.

#######################################
# Print the manifest entries to apply, in order, as "name url" lines.
# Arguments:
#   $1 - manifest path
#   $2 - class (kernel or module)
#   $3 - architecture (amd64 or arm64)
#######################################
kernel_patch_list() {
  local manifest="$1" class="$2" arch="$3" stage
  for stage in common "${arch}"; do
    CLASS="${class}" STAGE="${stage}" yq \
      '.patches[] | select(.class == strenv(CLASS) and .stage == strenv(STAGE))
        | .name + " " + .url' "${manifest}"
  done
}

#######################################
# Download and apply the patches of one class to a kernel source tree.
# Arguments:
#   $1 - manifest path
#   $2 - class (kernel or module)
#   $3 - architecture (amd64 or arm64)
#   $4 - kernel version, e.g. 7.2.11
#   $5 - kernel source tree
# Returns:
#   Exits 1 when a patch cannot be downloaded or does not apply.
#######################################
kernel_apply_patches() {
  local manifest="$1" class="$2" arch="$3" version="$4" tree="$5"
  local series="${version%.*}" name url file
  [[ "${version}" == *.*.* ]] || series="${version}"
  while read -r name url; do
    [[ -n "${name}" ]] || continue
    url="${url//\{series\}/${series}}"
    url="${url//\{version\}/${version}}"
    file=$(mktemp)
    curl --retry 3 -fsSL "${url}" -o "${file}" \
      || {
        echo "ERROR: cannot download patch ${name}: ${url}" >&2
        exit 1
      }
    patch -d "${tree}" -p1 --no-backup-if-mismatch --dry-run <"${file}" >/dev/null \
      || {
        echo "ERROR: patch ${name} does not apply to ${version}: ${url}" >&2
        exit 1
      }
    patch -d "${tree}" -p1 --no-backup-if-mismatch <"${file}" >/dev/null
    rm -f "${file}"
    echo "applied patch ${name}"
  done < <(kernel_patch_list "${manifest}" "${class}" "${arch}")
}
