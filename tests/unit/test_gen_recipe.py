"""Unit tests for gen-recipe.py."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest

from tests.support.documents import YamlValue, load_json, mapping, sequence
from tests.support.modules import bare_loader, load_module

SCRIPT = (
    Path(__file__).resolve().parents[2] / "src" / "buildisopreinstall" / "usr" /
    "libexec" / "debian-bootc" / "gen-recipe.py"
)


@runtime_checkable
class _Script(Protocol):
    """Surface of gen-recipe.py used by the tests."""

    def _build_images(
        self,
        root: str,
        registry: str,
        distro: str,
        arch: str = ''
    ) -> list[dict[str, YamlValue]]:
        """List the image entries of one build context.

        Args:
            root: Directory holding the Containerfiles.
            registry: Image registry prefix.
            distro: Distribution display name.
            arch: Architecture filter, empty for every architecture.

        Returns:
            One entry per Containerfile and architecture.
        """
        ...

    def read_label(self, path: str, label: str) -> str:
        """Read one Containerfile label.

        Args:
            path: Containerfile path.
            label: Label key.

        Returns:
            The label value, empty when the file has no such label.
        """
        ...


class _Module(_Script):
    """Test-facing facade over the loaded script.

    The builder is a private helper of the script; the facade republishes it
    under a public name, so the tests call it like any other API and the private
    access stays inside one subclass of the protocol.
    """

    def __init__(self, script: _Script) -> None:
        """Store the loaded script.

        Args:
            script: The executed gen-recipe.py module.
        """
        self._script = script

    def _build_images(
        self,
        root: str,
        registry: str,
        distro: str,
        arch: str = ''
    ) -> list[dict[str, YamlValue]]:
        """Forward to the script builder.

        Args:
            root: Directory holding the Containerfiles.
            registry: Image registry prefix.
            distro: Distribution display name.
            arch: Architecture filter, empty for every architecture.

        Returns:
            One entry per Containerfile and architecture.
        """
        return self._script._build_images(root, registry, distro, arch)

    def read_label(self, path: str, label: str) -> str:
        """Forward to the script reader.

        Args:
            path: Containerfile path.
            label: Label key.

        Returns:
            The label value, empty when the file has no such label.
        """
        return self._script.read_label(path, label)

    def build_images(
        self,
        root: str,
        registry: str,
        distro: str,
        arch: str = ''
    ) -> list[dict[str, YamlValue]]:
        """List the image entries of one build context.

        Args:
            root: Directory holding the Containerfiles.
            registry: Image registry prefix.
            distro: Distribution display name.
            arch: Architecture filter, empty for every architecture.

        Returns:
            One entry per Containerfile and architecture.
        """
        return self._build_images(root, registry, distro, arch)


def _load() -> _Module:
    """Import gen-recipe.py (hyphenated name) as a module.

    Returns:
        The freshly executed ``gen-recipe`` module.

    Raises:
        TypeError: when the module lacks its test surface.
    """
    module = load_module('gen_recipe', SCRIPT)
    if not isinstance(module, _Script):
        raise TypeError('gen-recipe.py lacks its test surface')
    return _Module(module)


def test_build_images_covers_variants_and_arches(tmp_path: Path) -> None:
    """Each Containerfile yields one entry per arch; .iso is skipped.

    Args:
        tmp_path: Scratch directory holding the fake Containerfiles.
    """
    for name in (
        "Containerfile", "Containerfile.vendor", "Containerfile.iso",
        "Containerfile.base"
    ):
        _ = (tmp_path / name).write_text("FROM scratch\n", encoding="utf-8")
    images = _load().build_images(str(tmp_path), "reg/x", "Deb")
    assert [i["imgref"] for i in images] == [
        "reg/x:latest_amd64",
        "reg/x:latest_arm64",
        "reg/x:vendor_amd64",
        "reg/x:vendor_arm64",
    ]
    assert images[0]["name"] == "Deb Standard (amd64)"
    assert images[2]["name"] == "Deb Vendor (amd64)"


def test_build_images_bootloader_is_install_time_auto(tmp_path: Path) -> None:
    """Every generated entry leaves the bootloader to install-time detection.

    The bootloader must not be baked per variant: "auto" is resolved by
    fisherman from the firmware of the machine being installed to (UEFI →
    GRUB through bootupd, U-Boot boards → no bootc bootloader stage).

    Args:
        tmp_path: Scratch directory holding the fake Containerfiles.
    """
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    images = _load().build_images(str(tmp_path), "reg/x", "Deb")
    assert images
    assert all(i["bootloader"] == "auto" for i in images)


def test_main_updates_only_images_fields(tmp_path: Path) -> None:
    """Static recipe fields are preserved; imgref/images are replaced.

    Args:
        tmp_path: Scratch directory holding the Containerfile and recipe.
    """
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    recipe = tmp_path / "recipe.json"
    _ = recipe.write_text(
        json.dumps({
            "distro_name": "Deb",
            "branding": "keep",
            "imgref": "old"
        }),
        encoding="utf-8",
    )
    _ = subprocess.run(
        [sys.executable,
         str(SCRIPT), str(tmp_path),
         str(recipe)],
        check=True,
        capture_output=True,
        env={
            **os.environ, "IMAGE_REGISTRY": "reg/x"
        },
    )
    data = mapping(load_json(recipe.read_text(encoding="utf-8")))
    assert data["branding"] == "keep"
    assert data["imgref"] == "reg/x:latest_amd64"
    assert len(sequence(data["images"])) == 2


def test_main_writes_the_catalog_the_installer_reads(tmp_path: Path) -> None:
    """images.json (the installer's system override) mirrors the recipe.

    The installer loads /etc/bootc-installer/images.json and, when it is
    absent, the package's own copy, which lacks ``fallback_flatpaks``:
    ``KeyError: 'fallback_flatpaks'`` at image.py:150 killed the live session.

    Args:
        tmp_path: Scratch directory holding the Containerfile and recipe.
    """
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    recipe = tmp_path / "recipe.json"
    _ = recipe.write_text(
        json.dumps({
            "distro_name": "Deb",
            "fallback_flatpaks": []
        }),
        encoding="utf-8",
    )
    _ = subprocess.run(
        [sys.executable,
         str(SCRIPT), str(tmp_path),
         str(recipe)],
        check=True,
        capture_output=True,
        env={
            **os.environ, "IMAGE_REGISTRY": "reg/x"
        },
    )
    catalog = mapping(
        load_json((tmp_path / "images.json").read_text(encoding="utf-8"))
    )
    assert catalog == mapping(load_json(recipe.read_text(encoding="utf-8")))
    assert catalog["fallback_flatpaks"] == []
    assert catalog["images"]


def test_tracked_recipe_is_a_static_template_only() -> None:
    """The tracked recipe.json carries NO hardcoded image catalog (P-196b).

    src/buildisopreinstall/etc/bootc-installer/recipe.json is the STATIC
    template of the ISO build (branding, tour, steps…): the image catalog is
    generated from the Containerfiles by gen-recipe.py in every build path
    that consumes it. A catalog hardcoded in the tracked file would drift from
    what the CI is programmed to build.
    """
    tracked = (
        Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' /
        'etc' / 'bootc-installer' / 'recipe.json'
    )
    data = mapping(load_json(tracked.read_text(encoding='utf-8')))
    assert data['images'] == [], data['images']
    assert 'imgref' not in data
    assert data.get('distro_name'), 'static template fields must stay'


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
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    _ = (tmp_path /
         "Containerfile.vendor").write_text("FROM scratch\n", encoding="utf-8")
    images = _load().build_images(str(tmp_path), "reg/x", "Deb", "amd64")
    assert [i["imgref"] for i in images] == [
        "reg/x:latest_amd64",
        "reg/x:vendor_amd64",
    ]
    assert all("gpu" not in i for i in images)


def test_build_images_filters_on_arch(tmp_path: Path) -> None:
    """With an arch filter only matching images are listed.

    Args:
        tmp_path: Scratch directory holding the fake Containerfile.
    """
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    images = _load().build_images(str(tmp_path), "reg/x", "Deb", "arm64")
    assert [i["imgref"] for i in images] == ["reg/x:latest_arm64"]


def test_arches_label_limits_the_image(tmp_path: Path) -> None:
    """A Containerfile with the arches label is listed for those arches only.

    Args:
        tmp_path: Scratch directory holding the fake Containerfiles.
    """
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    _ = (tmp_path / "Containerfile.vendor").write_text(
        'FROM scratch\nLABEL org.daemoncores.arches="amd64"\n',
        encoding="utf-8",
    )
    module = _load()
    both = module.build_images(str(tmp_path), "reg/x", "Deb")
    assert [i["imgref"] for i in both] == [
        "reg/x:latest_amd64",
        "reg/x:latest_arm64",
        "reg/x:vendor_amd64",
    ]
    arm = module.build_images(str(tmp_path), "reg/x", "Deb", "arm64")
    assert [i["imgref"] for i in arm] == ["reg/x:latest_arm64"]


def test_eula_label_marks_only_that_image(tmp_path: Path) -> None:
    """The requires-eula label becomes the ``eula`` field of its entry only.

    Args:
        tmp_path: Scratch directory holding the fake Containerfiles.
    """
    _ = (tmp_path /
         "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    _ = (tmp_path / "Containerfile.vendor").write_text(
        'FROM scratch\nLABEL org.daemoncores.requires-eula="vendor"\n',
        encoding="utf-8",
    )
    images = _load().build_images(str(tmp_path), "reg/x", "Deb", "amd64")
    by_ref = {str(i["imgref"]): i for i in images}
    assert by_ref["reg/x:vendor_amd64"]["eula"] == "vendor"
    assert "eula" not in by_ref["reg/x:latest_amd64"]


def test_label_in_a_comment_is_ignored(tmp_path: Path) -> None:
    """Only a real LABEL instruction counts, not a commented one.

    Args:
        tmp_path: Scratch directory holding the fake Containerfile.
    """
    path = tmp_path / "Containerfile.x"
    _ = path.write_text(
        '# LABEL org.daemoncores.requires-eula="x"\nFROM scratch\n',
        encoding="utf-8",
    )
    assert _load().read_label(str(path), "org.daemoncores.requires-eula") == ""


def _run_script_entry(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> None:
    """Run gen-recipe.py as the __main__ module in this process.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        argv: Arguments after the script name.
    """
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), *argv])
    namespace = runpy.run_path(str(SCRIPT), run_name='__main__')
    assert isinstance(namespace, dict)


def test_main_in_process_writes_both_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The entry point replaces the catalog and mirrors it next to the recipe.

    Args:
        tmp_path: Scratch directory holding the Containerfile and recipe.
        monkeypatch: Pytest monkeypatch fixture.
    """
    _ = (tmp_path / 'Containerfile').write_text('FROM scratch\n')
    recipe = tmp_path / 'recipe.json'
    _ = recipe.write_text(json.dumps({'distro_name': 'Deb'}), encoding='utf-8')
    monkeypatch.setenv('IMAGE_REGISTRY', 'reg/x')
    _run_script_entry(monkeypatch, [str(tmp_path), str(recipe)])
    data = mapping(load_json(recipe.read_text(encoding='utf-8')))
    assert data['imgref'] == 'reg/x:latest_amd64'
    assert (tmp_path / 'images.json').is_file()


def test_main_in_process_with_no_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty build context leaves the default image reference empty.

    Args:
        tmp_path: Scratch directory holding the recipe.
        monkeypatch: Pytest monkeypatch fixture.
    """
    recipe = tmp_path / 'recipe.json'
    _ = recipe.write_text(json.dumps({'distro_name': 'Deb'}), encoding='utf-8')
    monkeypatch.delenv('IMAGE_REGISTRY', raising=False)
    _run_script_entry(monkeypatch, [str(tmp_path), str(recipe)])
    data = mapping(load_json(recipe.read_text(encoding='utf-8')))
    assert data['imgref'] == ''
    assert data['images'] == []


def test_main_in_process_rejects_a_wrong_argument_count(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The entry point exits with status 1 when argv is incomplete.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    with pytest.raises(SystemExit) as exit_info:
        _run_script_entry(monkeypatch, [])
    assert exit_info.value.code == 1


def test_loader_guard_rejects_a_module_without_the_surface(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The facade refuses a module that lacks the tested helpers.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(sys.modules[__name__], 'load_module', bare_loader)
    with pytest.raises(TypeError, match='lacks its test surface'):
        _ = _load()
