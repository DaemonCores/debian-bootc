"""Unit tests for the bib overlay script ``patch_dracut.py``.

The script rewrites osbuild's ``org.osbuild.dracut`` stage so the live ISO
initramfs gets the ``debian-bootc-live`` module (Debian has no ``anaconda``
module). It is applied here to a stub stage with the same ``main`` shape and run
against a fake module tree, with directories named exactly as dracut names them:
``<nn><name>`` (``88debian-bootc-live``, no separator after the digits).

Regression: CI run 45026281529 shipped a check that split the directory name on
its first hyphen (``88debian-bootc-live`` -> ``bootc-live``), so every ISO job
died with ``dracut module debian-bootc-live missing from the tree``.
"""

import glob
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'bootc-image-builder-src' / 'patch_dracut.py'
)

STUB_STAGE = '''def main(tree, options):
    kernels = options["kernel"]
    add_modules = options.get("add_modules", [])
    modules = options.get("modules", [])
    extra = options.get("extra", [])
    return add_modules, modules
'''

Main = Callable[[str, dict[str, Any]], tuple[list[str], list[str]]]

CI_ADD_MODULES = [
    'pollcdrom',
    'qemu',
    'qemu-net',
    'biosdevname',
    'fips',
    'anaconda',
    'prefixdevname-tools',
]


@pytest.fixture
def patched_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Main:
    """Apply patch_dracut.py to a stub stage and return its ``main``.

    Args:
        tmp_path: Pytest temporary directory.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        The ``main`` function of the patched stub stage.
    """
    stage = tmp_path / 'org.osbuild.dracut'
    stage.write_text(STUB_STAGE)
    real_glob = glob.glob
    monkeypatch.setattr(
        glob, 'glob', lambda pattern, *a, **k: [str(stage)]
        if 'org.osbuild.dracut' in pattern else real_glob(pattern, *a, **k)
    )
    runpy.run_path(str(SCRIPT))
    namespace: dict[str, Any] = {}
    exec(compile(stage.read_text(), str(stage), 'exec'), namespace)
    return namespace['main']


def _tree(root: Path, *modules: str) -> Path:
    """Create a fake tree holding the given dracut module directories.

    Args:
        root: Directory that becomes the tree root.
        *modules: Module directory names, e.g. ``88debian-bootc-live``.

    Returns:
        The tree root.
    """
    md = root / 'usr' / 'lib' / 'dracut' / 'modules.d'
    md.mkdir(parents=True)
    for name in modules:
        (md / name).mkdir()
    return root


def test_live_module_added_when_present(
    patched_main: Main, tmp_path: Path
) -> None:
    """Anaconda requested + 88debian-bootc-live in the tree -> module added.

    Args:
        patched_main: Patched stub stage ``main``.
        tmp_path: Pytest temporary directory.
    """
    tree = _tree(
        tmp_path / 'tree', '88debian-bootc-live', '90dmsquash-live', '90qemu'
    )
    add, _ = patched_main(
        str(tree), {
            'kernel': ['k'],
            'add_modules': list(CI_ADD_MODULES)
        }
    )
    assert 'debian-bootc-live' in add
    assert 'anaconda' not in add


def test_live_module_missing_fails_the_build(
    patched_main: Main, tmp_path: Path
) -> None:
    """Anaconda requested, module absent -> hard error.

    Args:
        patched_main: Patched stub stage ``main``.
        tmp_path: Pytest temporary directory.
    """
    tree = _tree(tmp_path / 'tree', '90dmsquash-live', '90qemu')
    with pytest.raises(RuntimeError, match='debian-bootc-live missing'):
        patched_main(
            str(tree), {
                'kernel': ['k'],
                'add_modules': list(CI_ADD_MODULES)
            }
        )


def test_no_requirement_without_anaconda(
    patched_main: Main, tmp_path: Path
) -> None:
    """No anaconda requested -> live module neither required nor added.

    Args:
        patched_main: Patched stub stage ``main``.
        tmp_path: Pytest temporary directory.
    """
    tree = _tree(tmp_path / 'tree', '90qemu')
    add, _ = patched_main(str(tree), {'kernel': ['k'], 'add_modules': ['qemu']})
    assert 'debian-bootc-live' not in add


def test_live_module_ships_in_the_overlay() -> None:
    """The overlay the Containerfile copies into the tree holds the module."""
    root = SCRIPT.parents[3] / 'src' / 'buildisopreinstall' / 'usr' / 'lib' / \
        'dracut' / 'modules.d' / '88debian-bootc-live'
    for name in (
        'module-setup.sh', 'inst-stage2-lib.sh', 'parse-inst-stage2.sh',
        'live-generator.sh'
    ):
        assert (root / name).is_file(), name
