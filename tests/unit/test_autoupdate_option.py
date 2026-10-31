"""Wiring of the automatic-update switch of the installer."""

import json
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / 'workflows' / 'bootc-debs-builder'
MANIFEST = BUILDER / 'packages.yml'
RECIPE = (
    ROOT / 'src' / 'buildisopreinstall' / 'etc' / 'bootc-installer' /
    'recipe.json'
)


def _entry(name: str) -> dict[str, Any]:
    """Return one ``packages.yml`` entry.

    Args:
        name: Package name.

    Returns:
        The manifest entry.
    """
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))
    return next(p for p in data['packages'] if p['name'] == name)


def test_installer_step_is_in_the_recipe() -> None:
    """The recipe offers the autoupdate step after the encryption one."""
    steps = json.loads(RECIPE.read_text())['steps']
    assert steps['autoupdate'] == {'template': 'autoupdate'}
    keys = list(steps)
    assert keys.index('autoupdate') == keys.index('encryption') + 1


def _overlay_text(name: str) -> str:
    """Return the concatenated text of one source overlay.

    Args:
        name: Overlay directory name under the builder directory.

    Returns:
        Every patch and added file of the overlay, joined.
    """
    return '\n'.join(
        f.read_text() for f in sorted((BUILDER / name).rglob('*'))
        if f.is_file() and '__pycache__' not in f.parts
    )


def test_overlays_are_built_in_and_hashed() -> None:
    """Both source overlays are in ``sources`` and applied by the build."""
    for name in ('fisherman', 'bootc-installer'):
        entry = _entry(name)
        assert f'{name}-src' in entry['sources']
        assert (BUILDER / f'{name}-src' / 'patches.lock.json').is_file()
        call = (
            'deb_src_overlay "${SAVE_PWD}/workflows/bootc-debs-builder/'
            f'{name}-src"'
        )
        assert call in entry['build']


def test_installer_choice_reaches_the_recipe_field() -> None:
    """The installer writes ``autoUpdate`` and fisherman masks the timer."""
    installer = _overlay_text('bootc-installer-src')
    assert 'recipe["autoUpdate"] = False' in installer
    assert '"autoupdate": BootcDefaultAutoupdate' in installer
    fisherman = _overlay_text('fisherman-src')
    assert 'json:"autoUpdate,omitempty"' in fisherman
    assert 'bootc-fetch-apply-updates.timer' in fisherman
    assert '"/dev/null"' in fisherman
