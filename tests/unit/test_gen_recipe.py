"""Unit tests for gen-recipe.py."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

SCRIPT = (
    Path(__file__).resolve().parents[2] / "src" / "buildisopreinstall" / "usr" /
    "libexec" / "debian-bootc" / "gen-recipe.py"
)


def _load() -> ModuleType:
    """Import gen-recipe.py (hyphenated name) as a module.

    Returns:
        The freshly executed ``gen-recipe`` module.
    """
    spec = importlib.util.spec_from_file_location("gen_recipe", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_images_covers_variants_and_arches(tmp_path: Path) -> None:
    """Each Containerfile yields one entry per arch; .iso is skipped.

    Args:
        tmp_path: Scratch directory holding the fake Containerfiles.
    """
    for name in (
        "Containerfile", "Containerfile.minimal", "Containerfile.iso",
        "Containerfile.base"
    ):
        (tmp_path / name).write_text("FROM scratch\n", encoding="utf-8")
    images = _load()._build_images(str(tmp_path), "reg/x", "Deb")
    assert [i["imgref"] for i in images] == [
        "reg/x:latest_amd64",
        "reg/x:latest_arm64",
        "reg/x:minimal_amd64",
        "reg/x:minimal_arm64",
    ]
    assert images[0]["name"] == "Deb Standard (amd64)"
    assert images[2]["name"] == "Deb Minimal (amd64)"


def test_main_updates_only_images_fields(tmp_path: Path) -> None:
    """Static recipe fields are preserved; imgref/images are replaced.

    Args:
        tmp_path: Scratch directory holding the Containerfile and recipe.
    """
    (tmp_path / "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    recipe = tmp_path / "recipe.json"
    recipe.write_text(
        json.dumps({
            "distro_name": "Deb",
            "branding": "keep",
            "imgref": "old"
        }),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable,
         str(SCRIPT), str(tmp_path),
         str(recipe)],
        check=True,
        capture_output=True,
        env={
            **os.environ, "IMAGE_REGISTRY": "reg/x"
        },
    )
    data = json.loads(recipe.read_text(encoding="utf-8"))
    assert data["branding"] == "keep"
    assert data["imgref"] == "reg/x:latest_amd64"
    assert len(data["images"]) == 2


def test_main_usage_error() -> None:
    """Wrong argument count exits with status 1."""
    result = subprocess.run([sys.executable, str(SCRIPT)],
                            capture_output=True,
                            check=False)
    assert result.returncode == 1


def test_build_images_lists_no_gpu_twins(tmp_path: Path) -> None:
    """One entry per Containerfile and arch: the GPU profile is not an image.

    Args:
        tmp_path: Scratch directory holding the fake Containerfiles.
    """
    (tmp_path / "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path /
     "Containerfile.minimal").write_text("FROM scratch\n", encoding="utf-8")
    images = _load()._build_images(str(tmp_path), "reg/x", "Deb", "amd64")
    assert [i["imgref"] for i in images] == [
        "reg/x:latest_amd64",
        "reg/x:minimal_amd64",
    ]
    assert all("gpu" not in i for i in images)


def test_build_images_filters_on_arch(tmp_path: Path) -> None:
    """With an arch filter only matching images are listed.

    Args:
        tmp_path: Scratch directory holding the fake Containerfile.
    """
    (tmp_path / "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    images = _load()._build_images(str(tmp_path), "reg/x", "Deb", "arm64")
    assert [i["imgref"] for i in images] == ["reg/x:latest_arm64"]
