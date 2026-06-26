#!/bin/bash
# inject-banners-iso.sh — Replace Anaconda banners inside a Fedora boot ISO
# Usage: inject-banners-iso.sh <source.iso> <dest.iso>
#
# Reads from assets/banner/:
#   anaconda-sidebar.png  → sidebar background (sidebar-bg.png)
#   anaconda-logo.png     → logo overlaid on sidebar (sidebar-logo.png)
#                           auto-cleared (1×1 transparent) if absent but
#                           sidebar.png is present, to hide the Fedora logo
#   anaconda-topbar.png   → spoke navigation bar (topbar-bg.png)
#   anaconda-header.png   → hub/progress header (anaconda_header.png)
#
# Files are replaced in ALL variants (root + server/ + workstation/ etc.)
# so the branding applies regardless of which product CSS Anaconda loads.
#
# Requirements: unsquashfs, mksquashfs, xorriso, convert (ImageMagick)

set -euo pipefail

SRC_ISO="${1:?Usage: $0 <source.iso> <dest.iso> [display-name]}"
DST_ISO="${2:?Usage: $0 <source.iso> <dest.iso> [display-name]}"
PRODUCT_NAME="${3:-}"   # display name passed from CI (e.g. "Debian Bootc")
BANNER_DIR="assets/banner"

SIDEBAR="${BANNER_DIR}/anaconda-sidebar.png"
LOGO="${BANNER_DIR}/anaconda-logo.png"
TOPBAR="${BANNER_DIR}/anaconda-topbar.png"
HEADER="${BANNER_DIR}/anaconda-header.png"

[[ ! -f "$SIDEBAR" && ! -f "$LOGO" && \
   ! -f "$TOPBAR" && ! -f "$HEADER" ]] && {
  echo "[banners] No banner assets found, skipping"
  exit 0
}

WORKDIR=$(mktemp -d)
trap 'umount "$WORKDIR/iso-mnt"    2>/dev/null || true
      umount "$WORKDIR/rootfs-mount" 2>/dev/null || true
      rm -rf "$WORKDIR"' EXIT

# APRÈS (loop mount — kernel, pas de dépendance au format ISO)
echo "[banners] Extracting ISO..."
mkdir -p "$WORKDIR/iso-mnt" "$WORKDIR/iso-root"
mount -o loop,ro "$SRC_ISO" "$WORKDIR/iso-mnt"
cp -a "$WORKDIR/iso-mnt/." "$WORKDIR/iso-root/"
umount "$WORKDIR/iso-mnt"
chmod -R u+w "$WORKDIR/iso-root"

INSTALL_IMG=""
for c in "$WORKDIR/iso-root/images/install.img" \
          "$WORKDIR/iso-root/images/squashfs.img"; do
  [[ -f "$c" ]] && { INSTALL_IMG="$c"; break; }
done
[[ -z "$INSTALL_IMG" ]] && { echo "[banners] ERROR: install.img not found"; exit 1; }

echo "[banners] Found: $INSTALL_IMG"
echo "[banners] Unsquashing installer environment..."
unsquashfs -d "$WORKDIR/squashfs-root" "$INSTALL_IMG"

ROOTFS_IMG="$WORKDIR/squashfs-root/LiveOS/rootfs.img"
USE_ROOTFS_IMG=false

if [[ -f "$ROOTFS_IMG" ]]; then
  echo "[banners] LiveOS/rootfs.img found — mounting"
  USE_ROOTFS_IMG=true
  mkdir -p "$WORKDIR/rootfs-mount"
  mount -o loop,rw "$ROOTFS_IMG" "$WORKDIR/rootfs-mount"
  PIXMAPS="$WORKDIR/rootfs-mount/usr/share/anaconda/pixmaps"
else
  echo "[banners] No LiveOS/rootfs.img — using squashfs-root directly"
  PIXMAPS="$WORKDIR/squashfs-root/usr/share/anaconda/pixmaps"
fi

_replace() {
  local src="$1" target="$2"
  [[ ! -f "$PIXMAPS/$target" ]] && return 0   # fichier absent dans cette variante → skip
  cp "$src" "$PIXMAPS/$target"
  echo "[banners]   → $target"
}

# Génère un PNG transparent 1×1 si sidebar remplacée mais pas le logo
# (pour masquer le logo Fedora qui s'affiche par-dessus le fond)
TRANSPARENT=""
if [[ -f "$SIDEBAR" && ! -f "$LOGO" ]]; then
  TRANSPARENT="$WORKDIR/transparent.png"
  convert -size 1x1 xc:none "$TRANSPARENT"
  echo "[banners] No anaconda-logo.png — will clear sidebar-logo.png with transparent PNG"
fi

# Remplace dans toutes les variantes trouvées
VARIANTS=("" "server" "workstation" "silverblue" "atomic" "cloud")

for variant in "${VARIANTS[@]}"; do
  prefix="${variant:+$variant/}"

  if [[ -f "$SIDEBAR" ]]; then
    echo "[banners] sidebar-bg.png (${prefix:-root}):"
    _replace "$SIDEBAR" "${prefix}sidebar-bg.png"
  fi

  if [[ -f "$LOGO" ]]; then
    echo "[banners] sidebar-logo.png (${prefix:-root}):"
    _replace "$LOGO" "${prefix}sidebar-logo.png"
  elif [[ -n "$TRANSPARENT" ]]; then
    echo "[banners] sidebar-logo.png (${prefix:-root}) → transparent:"
    _replace "$TRANSPARENT" "${prefix}sidebar-logo.png"
  fi

  if [[ -f "$TOPBAR" ]]; then
    echo "[banners] topbar-bg.png (${prefix:-root}):"
    _replace "$TOPBAR" "${prefix}topbar-bg.png"
  fi
done

# anaconda_header.png n'existe qu'à la racine
if [[ -f "$HEADER" ]]; then
  echo "[banners] anaconda_header.png (root):"
  _replace "$HEADER" "anaconda_header.png"
fi

# Inject flat design CSS overrides if provided
if [[ -f "assets/banner/flat-overrides.css" ]]; then
  SERVER_CSS="$PIXMAPS/server/fedora-server.css"
  if [[ -f "$SERVER_CSS" ]]; then
    cp "$SERVER_CSS" "${SERVER_CSS}.bak"
    cat "assets/banner/flat-overrides.css" >> "$SERVER_CSS"
    echo "[banners] → flat-overrides.css appended to server/fedora-server.css"
  fi
fi

if [[ "$USE_ROOTFS_IMG" == true ]]; then
  umount "$WORKDIR/rootfs-mount"
fi

# Inject anaconda config to disable Users module directly into the installer squashfs
ANACONDA_CONF="$WORKDIR/squashfs-root/etc/anaconda/conf.d/99-disable-users.conf"
mkdir -p "$(dirname "$ANACONDA_CONF")"
printf '%s\n' \
  '[Anaconda]' \
  'forbidden_modules =' \
  '  org.fedoraproject.Anaconda.Modules.Users' \
  'optional_modules =' \
  '  org.fedoraproject.Anaconda.Modules.Localization' \
  '  org.fedoraproject.Anaconda.Modules.Network' \
  '  org.fedoraproject.Anaconda.Modules.Payloads' \
  '  org.fedoraproject.Anaconda.Modules.Storage' \
  '  org.fedoraproject.Anaconda.Modules.Services' \
  '  org.fedoraproject.Anaconda.Modules.Timezone' \
  '  org.fedoraproject.Anaconda.Modules.Security' \
  '  org.fedoraproject.Anaconda.Modules.Subscription' \
  '  org.fedoraproject.Anaconda.Addons.*' \
  > "$ANACONDA_CONF"
echo "[banners] → etc/anaconda/conf.d/99-disable-users.conf injected (Users forbidden, Addons optional)"

# Patch product name: .buildstamp controls "FEDORA 44" in the Anaconda header/welcome title
BUILDSTAMP="$WORKDIR/squashfs-root/.buildstamp"
if [[ -n "$PRODUCT_NAME" && -f "$BUILDSTAMP" ]]; then
  sed -i \
    -e "s|^Product=.*|Product=${PRODUCT_NAME}|" \
    -e "s|^Version=.*|Version=|" \
    -e "s|^Variant=.*|Variant=|" \
    "$BUILDSTAMP"
  echo "[banners] → .buildstamp patched (Product=${PRODUCT_NAME})"
fi

# Patch os-release display name (keep ID=fedora + VARIANT_ID=server for profile detection)
OS_RELEASE="$WORKDIR/squashfs-root/etc/os-release"
if [[ -n "$PRODUCT_NAME" && -f "$OS_RELEASE" ]]; then
  sed -i \
    -e "s|^NAME=.*|NAME=\"${PRODUCT_NAME}\"|" \
    -e "s|^PRETTY_NAME=.*|PRETTY_NAME=\"${PRODUCT_NAME}\"|" \
    "$OS_RELEASE"
  echo "[banners] → etc/os-release patched (NAME=${PRODUCT_NAME})"
fi

echo "[banners] Re-squashing..."
mksquashfs "$WORKDIR/squashfs-root" "$WORKDIR/new-install.img" \
  -comp xz -Xbcj x86 -b 1M -noappend -quiet
mv "$WORKDIR/new-install.img" "$INSTALL_IMG"

echo "[banners] Rebuilding ISO..."
xorriso \
  -return_with SORRY 0 \
  -indev  "$SRC_ISO" \
  -outdev "$DST_ISO" \
  -map    "$INSTALL_IMG" /images/$(basename "$INSTALL_IMG") \
  -boot_image any replay 2>/dev/null

echo "[banners] Done: $DST_ISO"