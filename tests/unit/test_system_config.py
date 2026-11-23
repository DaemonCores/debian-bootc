"""System step of the installer: hostname, root password, sudo, SSH root."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from tests.support.documents import (
    YamlValue,
    load_json,
    load_yaml,
    mapping,
    sequence,
    text,
)
from tests.support.modules import load_module

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / 'workflows' / 'bootc-debs-builder'
MANIFEST = BUILDER / 'packages.yml'
RECIPE = (
    ROOT / 'src' / 'buildisopreinstall' / 'etc' / 'bootc-installer' /
    'recipe.json'
)
INSTALLER = BUILDER / 'bootc-installer-src'
FISHERMAN = BUILDER / 'fisherman-src'


@runtime_checkable
class _Script(Protocol):
    """Surface of ``system_config.py`` used by the tests."""

    def valid_hostname(self, hostname: str) -> bool:
        """Tell whether a hostname is a valid RFC 1123 label.

        Args:
            hostname: Candidate hostname.

        Returns:
            True when letters, digits and inner hyphens only.
        """
        ...

    def valid_root_password(self, password: str, confirmation: str) -> bool:
        """Tell whether the root password is long enough and confirmed.

        Args:
            password: First entry.
            confirmation: Second entry.

        Returns:
            True when both match and reach the minimum length.
        """
        ...

    def user_groups(self, base: list[str], sudo: bool) -> list[str]:
        """Compute the supplementary groups of the created user.

        Args:
            base: Groups the installer already assigns.
            sudo: Whether the user keeps the admin group.

        Returns:
            The groups to assign, without duplicates.
        """
        ...

    def apply_system(
        self,
        recipe: dict[str, YamlValue],
        system: Mapping[str, YamlValue] | None,
    ) -> None:
        """Merge the ``system`` step result into a fisherman recipe.

        Args:
            recipe: Fisherman recipe being built.
            system: The ``system`` entry of the merged finals, or None.
        """
        ...


def _load() -> _Script:
    """Load ``system_config.py`` straight from the installer overlay.

    Returns:
        The executed module, imported without any GTK dependency.

    Raises:
        TypeError: when the module lacks its test surface.
    """
    module = load_module(
        'system_config', INSTALLER / 'utils' / 'system_config.py'
    )
    if not isinstance(module, _Script):
        raise TypeError('system_config.py lacks its test surface')
    return module


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


def _entry(name: str) -> dict[str, YamlValue]:
    """Return one ``packages.yml`` entry.

    Args:
        name: Package name.

    Returns:
        The manifest entry.

    Raises:
        KeyError: when no entry carries that name.
    """
    data = mapping(load_yaml(MANIFEST.read_text()))
    for entry in sequence(data['packages']):
        item = mapping(entry)
        if text(item['name']) == name:
            return item
    raise KeyError(name)


def _groups(recipe: dict[str, YamlValue]) -> list[str]:
    """Return the ``user.groups`` list of a recipe.

    Args:
        recipe: Fisherman recipe being built.

    Returns:
        The group names assigned to the created user.
    """
    return [
        text(group) for group in sequence(mapping(recipe['user'])['groups'])
    ]


def test_hostname_validation() -> None:
    """Only RFC 1123 labels pass."""
    m = _load()
    for good in ('a', 'my-pc', 'PC01', 'x' * 63):
        assert m.valid_hostname(good), good
    for bad in ('', '-a', 'a-', 'a_b', 'a.b', 'x' * 64, 'é'):
        assert not m.valid_hostname(bad), bad


def test_root_password_needs_length_and_confirmation() -> None:
    """Eight characters minimum and both entries equal."""
    m = _load()
    assert m.valid_root_password('12345678', '12345678')
    assert not m.valid_root_password('1234567', '1234567')
    assert not m.valid_root_password('12345678', '12345679')
    assert not m.valid_root_password('', '')


def test_groups_follow_the_sudo_choice() -> None:
    """The admin group is kept or dropped, Debian groups always added."""
    m = _load()
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
    m = _load()
    recipe: dict[str, YamlValue] = {
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
    assert 'sudo' not in _groups(recipe)


def test_apply_system_without_step_changes_nothing() -> None:
    """A skipped step leaves the recipe as it was."""
    m = _load()
    recipe: dict[str, YamlValue] = {
        'user': {
            'username': 'u',
            'groups': ['sudo']
        }
    }
    m.apply_system(recipe, None)
    assert recipe == {'user': {'username': 'u', 'groups': ['sudo']}}


def test_no_user_means_no_group_edit() -> None:
    """With no created user only the root settings are written."""
    m = _load()
    recipe: dict[str, YamlValue] = {'user': {'username': '', 'groups': []}}
    m.apply_system(recipe, {'rootPassword': 'longenough', 'sudo': True})
    assert _groups(recipe) == []
    assert recipe['rootPassword'] == 'longenough'


def test_step_is_in_the_recipe_after_the_user_step() -> None:
    """The ISO recipe offers the system step right after the user one."""
    steps = mapping(mapping(load_json(RECIPE.read_text()))['steps'])
    keys = list(steps)
    assert steps['system'] == {'template': 'system'}
    assert keys.index('system') == keys.index('user') + 1


def test_overlays_are_built_in_and_hashed() -> None:
    """Both source overlays are in ``sources`` and applied by the build."""
    for name in ('fisherman', 'bootc-installer'):
        entry = _entry(name)
        sources = [text(item) for item in sequence(entry['sources'])]
        assert f'{name}-src' in sources
        call = (
            'deb_src_overlay "${SAVE_PWD}/workflows/bootc-debs-builder/'
            f'{name}-src"'
        )
        assert call in text(entry['build'])


def test_installer_fields_match_the_fisherman_recipe() -> None:
    """The recipe keys written by the installer are read by fisherman."""
    installer = _overlay_text(INSTALLER)
    assert 'recipe["rootPassword"]' in installer
    assert 'recipe["sshRootLogin"]' in installer
    fisherman = _overlay_text(FISHERMAN)
    assert 'json:"rootPassword,omitempty"' in fisherman
    assert 'json:"sshRootLogin,omitempty"' in fisherman
    assert '01-permitrootlogin.conf' in fisherman
