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
# Download the patches of one class, check the sha256 of the files they touch
# against kernel/patches.lock.json, then apply them to a kernel source tree.
# The guard runs on the pristine tree, before any patch: a touched file that
# changed upstream refuses the build (the last good deb stays published) until
# the lock is refreshed. Set PATCH_GUARD_UPDATE=1 to rewrite the lock instead.
# Arguments:
#   $1 - manifest path
#   $2 - class (kernel or module)
#   $3 - architecture (amd64 or arm64)
#   $4 - kernel version, e.g. 7.2.11
#   $5 - kernel source tree
# Returns:
#   Exits 1 when a patch cannot be downloaded, a guarded file changed or a
#   patch does not apply.
#######################################
kernel_apply_patches() {
  local manifest="$1" class="$2" arch="$3" version="$4" tree="$5"
  local series="${version%.*}" name url dir file
  local -a names=() files=()
  [[ "${version}" == *.*.* ]] || series="${version}"
  dir=$(mktemp -d)
  while read -r name url; do
    [[ -n "${name}" ]] || continue
    url="${url//\{series\}/${series}}"
    url="${url//\{version\}/${version}}"
    file="${dir}/${#files[@]}.patch"
    curl --retry 3 -fsSL "${url}" -o "${file}" \
      || {
        echo "ERROR: cannot download patch ${name}: ${url}" >&2
        exit 1
      }
    names+=("${name}")
    files+=("${file}")
  done < <(kernel_patch_list "${manifest}" "${class}" "${arch}")
  ((${#files[@]})) || return 0

  local guard=()
  [[ "${PATCH_GUARD_UPDATE:-0}" != 1 ]] || guard=(--update)
  python3 "${CI_SCRIPTS}/patch_guard.py" --tree "${tree}" \
    --lock "$(dirname "${manifest}")/patches.lock.json" "${guard[@]}" "${files[@]}" \
    || {
      echo "ERROR: a file touched by the patches changed upstream" >&2
      exit 1
    }

  local i
  for i in "${!files[@]}"; do
    patch -d "${tree}" -p1 --no-backup-if-mismatch --dry-run <"${files[i]}" >/dev/null \
      || {
        echo "ERROR: patch ${names[i]} does not apply to ${version}" >&2
        exit 1
      }
    patch -d "${tree}" -p1 --no-backup-if-mismatch <"${files[i]}" >/dev/null
    echo "applied patch ${names[i]}"
  done
  rm -rf "${dir}"
}
