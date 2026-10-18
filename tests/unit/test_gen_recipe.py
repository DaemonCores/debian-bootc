"""Unit tests for scripts/gen-recipe.py."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gen-recipe.py"


def _load():
    """Import gen-recipe.py (hyphenated name) as a module."""
    spec = importlib.util.spec_from_file_location("gen_recipe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_images_covers_variants_and_arches(tmp_path):
    """Each Containerfile yields one entry per arch; .iso is skipped."""
    for name in ("Containerfile", "Containerfile.minimal", "Containerfile.iso"):
        (tmp_path / name).write_text("FROM scratch\n", encoding="utf-8")
    images = _load()._build_images(str(tmp_path), "reg/x", "Deb")
    assert [i["imgref"] for i in images] == [
        "reg/x:latest-amd64-autoupdate",
        "reg/x:latest-arm64-autoupdate",
        "reg/x:minimal-amd64-autoupdate",
        "reg/x:minimal-arm64-autoupdate",
    ]
    assert images[0]["name"] == "Deb Standard (amd64)"
    assert images[2]["name"] == "Deb Minimal (amd64)"


def test_main_updates_only_images_fields(tmp_path):
    """Static recipe fields are preserved; imgref/images are replaced."""
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
        env={"IMAGE_REGISTRY": "reg/x"},
    )
    data = json.loads(recipe.read_text(encoding="utf-8"))
    assert data["branding"] == "keep"
    assert data["imgref"] == "reg/x:latest-amd64-autoupdate"
    assert len(data["images"]) == 2


def test_main_usage_error():
    """Wrong argument count exits with status 1."""
    result = subprocess.run([sys.executable, str(SCRIPT)],
                            capture_output=True,
                            check=False)
    assert result.returncode == 1


def test_build_images_filters_on_arch(tmp_path):
    """With an arch filter only matching images are listed."""
    (tmp_path / "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    images = _load()._build_images(str(tmp_path), "reg/x", "Deb", "arm64")
    assert [i["imgref"] for i in images] == ["reg/x:latest-arm64-autoupdate"]
