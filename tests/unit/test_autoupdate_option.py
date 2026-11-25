"""Wiring of the automatic-update switch of the installer."""

from pathlib import Path

from tests.support.documents import (
    YamlValue,
    load_json,
    load_yaml,
    mapping,
    sequence,
    text,
)

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / 'workflows' / 'bootc-debs-builder'
MANIFEST = BUILDER / 'packages.yml'
RECIPE = (
    ROOT / 'src' / 'buildisopreinstall' / 'etc' / 'bootc-installer' /
    'recipe.json'
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
        if item['name'] == name:
            return item
    raise KeyError(name)


def test_installer_step_is_in_the_recipe() -> None:
    """The recipe offers the autoupdate step after the encryption one."""
    steps = mapping(mapping(load_json(RECIPE.read_text()))['steps'])
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
    for name, source in (('fisherman', 'fisherman-src'),
                         ('bootc-installer', 'bootc_installer')):
        entry = _entry(name)
        sources = [text(item) for item in sequence(entry['sources'])]
        assert source in sources
        # The overlay carries ONLY source: the .patch files. No
        # patches.lock.json in git (owner 2026-11-03): the sha256 reference is
        # computed and retained by patch_guard at build, build-local.
        assert list((BUILDER / source).rglob('*.patch')), name
        assert not list((BUILDER / source).rglob('patches.lock.json')), name
        call = (
            'deb_src_overlay "${SAVE_PWD}/workflows/bootc-debs-builder/'
            f'{source}"'
        )
        assert call in text(entry['build'])


def test_installer_choice_reaches_the_recipe_field() -> None:
    """The installer writes ``autoUpdate`` and fisherman masks the timer."""
    installer = _overlay_text('bootc_installer')
    assert 'recipe["autoUpdate"] = False' in installer
    assert '"autoupdate": BootcDefaultAutoupdate' in installer
    fisherman = _overlay_text('fisherman-src')
    assert 'json:"autoUpdate,omitempty"' in fisherman
    assert 'bootc-fetch-apply-updates.timer' in fisherman
    assert '"/dev/null"' in fisherman
