#!/usr/bin/env python3
"""gen-recipe.py — regenerate /etc/bootc-installer/recipe.json image list.

Usage:
    IMAGE_REGISTRY=ghcr.io/owner/repo python3 gen-recipe.py <ctx_dir> <recipe_path>

Args:
    ctx_dir: Directory containing the Containerfile* files to scan.
    recipe_path: Path to the recipe.json to update in-place (static fields kept).

The script replaces only the ``imgref`` and ``images`` fields; all other fields
(branding, tour, steps, …) are preserved from the existing file.

Reads ``IMAGE_REGISTRY`` from the environment.  Defaults to the DaemonCores
registry when the variable is absent (for local/manual builds).
"""

import json
import os
import sys
from typing import Any


def _build_images(
    ctx_dir: str,
    registry: str,
    distro_name: str,
) -> list[dict[str, Any]]:
    """Return the image list built from the Containerfile* files in ctx_dir.

    Args:
        ctx_dir: Directory containing Containerfile* files.
        registry: Container registry prefix (e.g. ghcr.io/owner/repo).
        distro_name: Distribution name read from the existing recipe.

    Returns:
        List of image descriptor dicts ready for recipe["images"].
    """
    arches = ["amd64", "arm64"]
    images: list[dict[str, Any]] = []

    containerfiles = sorted(
        cf for cf in os.listdir(ctx_dir)
        if cf.startswith("Containerfile")
        and os.path.isfile(os.path.join(ctx_dir, cf))
        and cf != "Containerfile.iso"
    )

    for cf in containerfiles:
        tag = "latest" if cf == "Containerfile" else cf[len("Containerfile."):]
        variant = "Standard" if tag == "latest" else tag.capitalize()
        for arch in arches:
            imgref = f"{registry}:{tag}-{arch}-autoupdate"
            images.append({
                "name": f"{distro_name} {variant} ({arch})",
                "imgref": imgref,
                "bootloader": "grub2",
                "filesystem": "btrfs",
                "composefs": False,
                "needs_user_creation": True,
                "filesystems": ["btrfs", "xfs"],
            })

    return images


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
        recipe: dict[str, Any] = json.load(fh)

    distro_name = str(recipe.get("distro_name", "Debian bootc"))
    images = _build_images(ctx_dir, registry, distro_name)

    recipe["imgref"] = images[0]["imgref"] if images else ""
    recipe["images"] = images

    with open(recipe_path, "w", encoding="utf-8") as fh:
        json.dump(recipe, fh, indent=4)
        fh.write("\n")


if __name__ == "__main__":
    main()
