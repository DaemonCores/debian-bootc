"""System step of the installer: hostname, root password, sudo, SSH root."""

import json
import types
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
INSTALLER = BUILDER / 'bootc-installer-src'
FISHERMAN = BUILDER / 'fisherman-src'


def _overlay_text(overlay: Path) -> str:
    """Return the concatenated text of one source overlay.

    Args:
        overlay: Overlay directory.

    Returns:
        Every patch and added file of the overlay, joined.
    """
    return '\n'.join(
        f.read_text() for f in sorted(overlay.rglob('*'))
        if f.is_file() and '__pycache__' not in f.parts
    )


def _module() -> types.ModuleType:
    """Load ``system_config.py`` straight from the installer overlay.

    Returns:
        The module, executed without any GTK dependency.
    """
    module = types.ModuleType('system_config')
    exec(
        compile((INSTALLER / 'bootc_installer' / 'utils' /
                 'system_config.py').read_text(), 'system_config.py', 'exec'),
        module.__dict__
    )
    return module


def _entry(name: str) -> dict[str, Any]:
    """Return one ``packages.yml`` entry.

    Args:
        name: Package name.

    Returns:
        The manifest entry.
    """
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))
    return next(p for p in data['packages'] if p['name'] == name)


def test_hostname_validation() -> None:
    """Only RFC 1123 labels pass."""
    m = _module()
    for good in ('a', 'my-pc', 'PC01', 'x' * 63):
        assert m.valid_hostname(good), good
    for bad in ('', '-a', 'a-', 'a_b', 'a.b', 'x' * 64, 'é'):
        assert not m.valid_hostname(bad), bad


def test_root_password_needs_length_and_confirmation() -> None:
    """Eight characters minimum and both entries equal."""
    m = _module()
    assert m.valid_root_password('12345678', '12345678')
    assert not m.valid_root_password('1234567', '1234567')
    assert not m.valid_root_password('12345678', '12345679')
    assert not m.valid_root_password('', '')


def test_groups_follow_the_sudo_choice() -> None:
    """The admin group is kept or dropped, Debian groups always added."""
    m = _module()
    base = ['sudo', 'docker', 'dialout']
    with_sudo = m.user_groups(base, True)
    without = m.user_groups(base, False)
    assert with_sudo[0] == 'sudo'
    assert 'sudo' not in without
    for groups in (with_sudo, without):
        assert len(groups) == len(set(groups))
        assert {'docker', 'dialout', 'adm', 'audio', 'netdev'} <= set(groups)
    assert m.user_groups(['sudo'], True).count('sudo') == 1


def test_apply_system_fills_the_recipe() -> None:
    """Root password, SSH policy and groups reach the recipe."""
    m = _module()
    recipe: dict[str, Any] = {
        'user': {
            'username': 'u',
            'groups': ['sudo', 'docker']
        }
    }
    m.apply_system(
        recipe, {
            'rootPassword': 'longenough',
            'sudo': False,
            'sshRootLogin': False
        }
    )
    assert recipe['rootPassword'] == 'longenough'
    assert recipe['sshRootLogin'] is False
    assert 'sudo' not in recipe['user']['groups']


def test_apply_system_without_step_changes_nothing() -> None:
    """A skipped step leaves the recipe as it was."""
    m = _module()
    recipe: dict[str, Any] = {'user': {'username': 'u', 'groups': ['sudo']}}
    m.apply_system(recipe, None)
    assert recipe == {'user': {'username': 'u', 'groups': ['sudo']}}


def test_no_user_means_no_group_edit() -> None:
    """With no created user only the root settings are written."""
    m = _module()
    recipe: dict[str, Any] = {'user': {'username': '', 'groups': []}}
    m.apply_system(recipe, {'rootPassword': 'longenough', 'sudo': True})
    assert recipe['user']['groups'] == []
    assert recipe['rootPassword'] == 'longenough'


def test_step_is_in_the_recipe_after_the_user_step() -> None:
    """The ISO recipe offers the system step right after the user one."""
    steps = json.loads(RECIPE.read_text())['steps']
    keys = list(steps)
    assert steps['system'] == {'template': 'system'}
    assert keys.index('system') == keys.index('user') + 1


def test_overlays_are_built_in_and_hashed() -> None:
    """Both source overlays are in ``sources`` and applied by the build."""
    for name in ('fisherman', 'bootc-installer'):
        entry = _entry(name)
        assert f'{name}-src' in entry['sources']
        call = (
            'deb_src_overlay "${SAVE_PWD}/workflows/bootc-debs-builder/'
            f'{name}-src"'
        )
        assert call in entry['build']


def test_installer_fields_match_the_fisherman_recipe() -> None:
    """The recipe keys written by the installer are read by fisherman."""
    installer = _overlay_text(INSTALLER)
    assert 'recipe["rootPassword"]' in installer
    assert 'recipe["sshRootLogin"]' in installer
    fisherman = _overlay_text(FISHERMAN)
    assert 'json:"rootPassword,omitempty"' in fisherman
    assert 'json:"sshRootLogin,omitempty"' in fisherman
    assert '01-permitrootlogin.conf' in fisherman
