"""Wiring of the automatic-update switch of the installer."""

import json
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'workflows' / 'bootc-debs-builder' / 'patches'
MANIFEST = ROOT / 'workflows' / 'bootc-debs-builder' / 'packages.yml'
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


def test_patches_are_built_in_and_hashed() -> None:
    """Both patches are listed in ``sources`` and applied by the build."""
    for name, patch in (('fisherman', 'fisherman-autoupdate.patch'),
                        ('bootc-installer',
                         'bootc-installer-autoupdate.patch')):
        entry = _entry(name)
        assert f'patches/{patch}' in entry['sources']
        assert (PATCHES / patch).is_file()
        assert f'patches/{patch}' in entry['build']


def test_installer_choice_reaches_the_recipe_field() -> None:
    """The installer writes ``autoUpdate`` and fisherman masks the timer."""
    installer = (PATCHES / 'bootc-installer-autoupdate.patch').read_text()
    assert 'recipe["autoUpdate"] = False' in installer
    assert '"autoupdate": BootcDefaultAutoupdate' in installer
    fisherman = (PATCHES / 'fisherman-autoupdate.patch').read_text()
    assert 'json:"autoUpdate,omitempty"' in fisherman
    assert 'bootc-fetch-apply-updates.timer' in fisherman
    assert '"/dev/null"' in fisherman
