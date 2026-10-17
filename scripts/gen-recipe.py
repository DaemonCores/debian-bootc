#!/usr/bin/env python3
"""
gen-recipe.py  —  regenerate /etc/bootc-installer/recipe.json image list.

Usage:
    IMAGE_REGISTRY=ghcr.io/owner/repo python3 gen-recipe.py <ctx_dir> <recipe_path>

<ctx_dir>      directory containing the Containerfile* files to scan
<recipe_path>  path to the recipe.json to update in-place (static fields kept)

The script replaces only the `imgref` and `images` fields; all other fields
(branding, tour, steps, …) are preserved from the existing file.

Reads IMAGE_REGISTRY from the environment.  Defaults to the DaemonCores
registry when the variable is absent (for local/manual builds).
"""
import json
import os
import sys


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: gen-recipe.py <ctx_dir> <recipe_path>", file=sys.stderr)
        sys.exit(1)

    ctx_dir, recipe_path = sys.argv[1], sys.argv[2]
    registry = os.environ.get("IMAGE_REGISTRY", "ghcr.io/daemoncores/debian-bootc")

    with open(recipe_path) as fh:
        recipe = json.load(fh)

    arches = ["amd64", "arm64"]
    images: list = []

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
                "name": f"{recipe['distro_name']} {variant} ({arch})",
                "imgref": imgref,
                "bootloader": "grub2",
                "filesystem": "btrfs",
                "composefs": False,
                "needs_user_creation": True,
                "filesystems": ["btrfs", "xfs"],
            })

    recipe["imgref"] = images[0]["imgref"] if images else ""
    recipe["images"] = images

    with open(recipe_path, "w") as fh:
        json.dump(recipe, fh, indent=4)
        fh.write("\n")


if __name__ == "__main__":
    main()
