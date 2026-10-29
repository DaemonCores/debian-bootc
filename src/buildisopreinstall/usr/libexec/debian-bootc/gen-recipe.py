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
"""

import json
import os
import sys
from typing import cast

JsonObject = dict[str, object]


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
    arches = [a for a in ("amd64", "arm64") if arch_filter in ("", a)]
    images: list[JsonObject] = []

    containerfiles = sorted(
        cf for cf in os.listdir(ctx_dir) if cf.startswith("Containerfile")
        and os.path.isfile(os.path.join(ctx_dir, cf)) and cf not in
        ("Containerfile.iso", "Containerfile.base")
    )

    for cf in containerfiles:
        tag = "latest" if cf == "Containerfile" else cf[len("Containerfile."):]
        variant = "Standard" if tag == "latest" else tag.capitalize()
        with open(cf_path(ctx_dir, cf), encoding="utf-8") as fh:
            content = fh.read()
        gpu_twins = (
            "org.daemoncores.gpu-ia-image" in content
            or "org.daemoncores.gpu-gaming-image" in content
        )
        for arch in arches:
            imgref = f"{registry}:{tag}_{arch}"
            images.append({
                "name": f"{distro_name} {variant} ({arch})",
                "imgref": imgref,
                "bootloader": "grub2",
                "filesystem": "btrfs",
                "composefs": False,
                "needs_user_creation": True,
                "filesystems": ["btrfs", "xfs"],
            })
            if gpu_twins:
                # GPU usage twins (wiki: GPU-Support.md). Listed AFTER the
                # public entries; the ia twin is deployed only when the
                # installer detects the GPU AND the EULA was accepted at
                # install, the gaming twin whenever a GPU is detected.
                # linux-modules-nvidia is an amd64-only plan deb (arm64 has
                # no shipped NVIDIA compute target): the ia twin exists
                # for amd64 only.
                for gpu_key, name_suffix, twin_tag, twin_arches in (
                    ("gaming", "Gaming", "-gaming", ("amd64", "arm64")),
                    ("ia", "IA", "-ia", ("amd64",)),
                ):
                    if arch not in twin_arches:
                        continue
                    entry: JsonObject = {
                        "name": (
                            f"{distro_name} {variant} {name_suffix} ({arch})"
                        ),
                        "imgref": f"{registry}:{tag}{twin_tag}_{arch}",
                        "bootloader": "grub2",
                        "filesystem": "btrfs",
                        "composefs": False,
                        "needs_user_creation": True,
                        "filesystems": ["btrfs", "xfs"],
                        "gpu": gpu_key,
                    }
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
