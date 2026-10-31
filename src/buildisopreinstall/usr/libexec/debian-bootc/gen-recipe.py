#!/usr/bin/env python3
"""gen-recipe.py — regenerate /etc/bootc-installer/recipe.json image list.

Usage:
    IMAGE_REGISTRY=ghcr.io/owner/repo \
        python3 gen-recipe.py <ctx_dir> <recipe_path>

Args:
    ctx_dir: Directory containing the Containerfile* files to scan.
    recipe_path: Path to the recipe.json to update in-place (static fields
        kept).

The script replaces only the ``imgref`` and ``images`` fields; all other fields
(branding, tour, steps, …) are preserved from the existing file.

Reads ``IMAGE_REGISTRY`` from the environment.  Defaults to the DaemonCores
registry when the variable is absent (for local/manual builds).  When ``ARCH``
is set (``amd64`` or ``arm64``), only images for that architecture are listed:
an installer ISO cannot install an image built for another CPU.

Two Containerfile labels shape an entry:

* ``org.daemoncores.arches`` (space or comma separated) limits the image to
  those architectures, the way the CI builds it.
* ``org.daemoncores.requires-eula`` names a license the installer must have
  accepted before it installs the image; it becomes the ``eula`` field of the
  entry, absent for every other image.
"""

import json
import os
import re
import sys
from typing import cast

JsonObject = dict[str, object]

ALL_ARCHES = ("amd64", "arm64")
LABEL_ARCHES = "org.daemoncores.arches"
LABEL_EULA = "org.daemoncores.requires-eula"


def read_label(path: str, label: str) -> str:
    """Read the value of a ``LABEL`` instruction from a Containerfile.

    Args:
        path: Containerfile path.
        label: Label key to look for.

    Returns:
        The value without quotes, empty when the label is absent.
    """
    pattern = re.compile(
        r"^\s*LABEL\s+" + re.escape(label) + r"=[\"']?([^\"'\n]*)"
    )
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line)
            if match:
                return match.group(1).strip()
    return ""


def _build_images(
    ctx_dir: str,
    registry: str,
    distro_name: str,
    arch_filter: str = "",
) -> list[JsonObject]:
    """Return the image list built from the Containerfile* files in ctx_dir.

    Args:
        ctx_dir: Directory containing Containerfile* files.
        registry: Container registry prefix (e.g. ghcr.io/owner/repo).
        distro_name: Distribution name read from the existing recipe.
        arch_filter: When non-empty, keep only this architecture.

    Returns:
        List of image descriptor dicts ready for recipe["images"].
    """
    arches = [a for a in ALL_ARCHES if arch_filter in ("", a)]
    images: list[JsonObject] = []

    containerfiles = sorted(
        cf for cf in os.listdir(ctx_dir) if cf.startswith("Containerfile")
        and os.path.isfile(os.path.join(ctx_dir, cf)) and cf not in
        ("Containerfile.iso", "Containerfile.base")
    )

    for cf in containerfiles:
        tag = "latest" if cf == "Containerfile" else cf[len("Containerfile."):]
        variant = "Standard" if tag == "latest" else tag.capitalize()
        path = cf_path(ctx_dir, cf)
        only = read_label(path, LABEL_ARCHES).replace(",", " ").split()
        eula = read_label(path, LABEL_EULA)
        for arch in arches:
            if only and arch not in only:
                continue
            imgref = f"{registry}:{tag}_{arch}"
            entry: JsonObject = {
                "name": f"{distro_name} {variant} ({arch})",
                "imgref": imgref,
                "bootloader": "grub2",
                "filesystem": "btrfs",
                "composefs": False,
                "needs_user_creation": True,
                "filesystems": ["btrfs", "xfs"],
            }
            if eula:
                entry["eula"] = eula
            images.append(entry)

    return images


def cf_path(ctx_dir: str, cf: str) -> str:
    """Join the context directory with a Containerfile name.

    Args:
        ctx_dir: Directory containing the Containerfile* files.
        cf: The Containerfile name.

    Returns:
        The joined path.
    """
    return os.path.join(ctx_dir, cf)


def main() -> None:
    """Entry point: update the recipe.json image list."""
    if len(sys.argv) != 3:
        print("usage: gen-recipe.py <ctx_dir> <recipe_path>", file=sys.stderr)
        sys.exit(1)

    ctx_dir, recipe_path = sys.argv[1], sys.argv[2]
    registry = os.environ.get(
        "IMAGE_REGISTRY",
        "ghcr.io/daemoncores/debian-bootc",
    )

    with open(recipe_path, encoding="utf-8") as fh:
        recipe = cast(JsonObject, json.load(fh))

    distro_name = str(recipe.get("distro_name", "Debian bootc"))
    images = _build_images(
        ctx_dir, registry, distro_name, os.environ.get("ARCH", "")
    )

    recipe["imgref"] = images[0]["imgref"] if images else ""
    recipe["images"] = images

    with open(recipe_path, "w", encoding="utf-8") as fh:
        json.dump(recipe, fh, indent=4)
        fh.write("\n")


if __name__ == "__main__":
    main()
