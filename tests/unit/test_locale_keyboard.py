"""Language and keyboard choices of the installer ``system`` step."""

import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest

from tests.support.documents import YamlValue
from tests.support.modules import bare_loader, load_module

BUILDER = Path(__file__
               ).resolve().parents[2] / 'workflows' / 'bootc-debs-builder'
INSTALLER = BUILDER / 'bootc_installer'
FISHERMAN = BUILDER / 'fisherman-src' / 'fisherman'

SUPPORTED = """\
# comment
en_US.UTF-8 UTF-8
en_US ISO-8859-1
fr_FR.UTF-8 UTF-8
sr_RS.UTF-8@latin UTF-8
eo.UTF-8 UTF-8
bad name.UTF-8 UTF-8
"""

BASE_LST = """\
! model
  pc105           Generic 105-key PC

! layout
  us              English (US)
  fr              French

! variant
  oss             fr: French (alt.)
  bepo            fr: French (Bepo)
  intl            us: English (US, intl., with dead keys)
  orphan          zz: Unknown layout
  nodesc          fr

! option
  grp             Switching to another layout
"""


@runtime_checkable
class _Script(Protocol):
    """Surface of ``locale_config.py`` used by the tests."""

    def valid_locale(self, locale: str) -> bool:
        """Tell whether a string is a glibc locale name.

        Args:
            locale: Candidate locale.

        Returns:
            True for the ``language[_TERRITORY].charset`` shape.
        """
        ...

    def valid_keyboard(
        self, layout: str, variant: str, model: str = ...
    ) -> bool:
        """Tell whether the three XKB names are acceptable.

        Args:
            layout: XKB layout.
            variant: XKB variant, empty for the layout default.
            model: XKB model.

        Returns:
            True when every name is an XKB token.
        """
        ...

    def supported_locales(self, path: str) -> list[str]:
        """List the UTF-8 locales the live system can generate.

        Args:
            path: glibc ``SUPPORTED`` file.

        Returns:
            The locale names, sorted.
        """
        ...

    def keyboard_layouts(self, path: str) -> list[tuple[str, str, str]]:
        """List the keyboard layouts and their variants.

        Args:
            path: XKB rules list.

        Returns:
            ``(layout, variant, description)`` triples, sorted.
        """
        ...

    def apply_locale(
        self, recipe: dict[str, YamlValue],
        system: Mapping[str, YamlValue] | None
    ) -> None:
        """Merge the language and keyboard of the step into a recipe.

        Args:
            recipe: Fisherman recipe being built.
            system: The ``system`` entry of the merged finals, or None.
        """
        ...


def _load() -> _Script:
    """Load ``locale_config.py`` straight from the installer overlay.

    Returns:
        The executed module, imported without any GTK dependency.

    Raises:
        TypeError: when the module lacks its test surface.
    """
    path = INSTALLER / 'utils' / 'locale_config.py'
    module = load_module('locale_config', path)
    if not isinstance(module, _Script):
        raise TypeError('locale_config.py lacks its test surface')
    return module


def test_locale_validation() -> None:
    """Only a glibc name with a charset passes."""
    m = _load()
    for good in ('fr_FR.UTF-8', 'eo.UTF-8', 'sr_RS.UTF-8@latin', 'C.UTF-8'):
        assert m.valid_locale(good), good
    for bad in (
        '', 'fr_FR', 'fr_FR.UTF-8\nLANG=C', 'fr FR.UTF-8', '../x.UTF-8'
    ):
        assert not m.valid_locale(bad), bad


def test_keyboard_validation() -> None:
    """Layout and model are XKB names, the variant may be empty."""
    m = _load()
    assert m.valid_keyboard('fr', 'oss')
    assert m.valid_keyboard('us,fr', '')
    assert not m.valid_keyboard('', '')
    assert not m.valid_keyboard('us\nX=1', '')
    assert not m.valid_keyboard('us', 'a b')
    assert not m.valid_keyboard('us', '', model='')


def test_supported_locales_keeps_valid_utf8_entries(tmp_path: Path) -> None:
    """Non UTF-8 charsets, comments and malformed names are dropped.

    Args:
        tmp_path: Pytest scratch directory.
    """
    m = _load()
    listing = tmp_path / 'SUPPORTED'
    _ = listing.write_text(SUPPORTED)
    assert m.supported_locales(str(listing)) == [
        'en_US.UTF-8', 'eo.UTF-8', 'fr_FR.UTF-8', 'sr_RS.UTF-8@latin'
    ]


def test_missing_lists_give_no_choice(tmp_path: Path) -> None:
    """An unreadable list leaves the image default, without an error.

    Args:
        tmp_path: Pytest scratch directory.
    """
    m = _load()
    assert m.supported_locales(str(tmp_path / 'none')) == []
    assert m.keyboard_layouts(str(tmp_path / 'none')) == []


def test_keyboard_layouts_join_variants_to_their_layout(tmp_path: Path) -> None:
    """Layouts and variants are listed together, sorted by description.

    Args:
        tmp_path: Pytest scratch directory.
    """
    m = _load()
    listing = tmp_path / 'base.lst'
    _ = listing.write_text(BASE_LST)
    assert m.keyboard_layouts(str(listing)) == [
        ('us', '', 'English (US)'),
        ('us', 'intl', 'English (US) - English (US, intl., with dead keys)'),
        ('fr', '', 'French'),
        ('fr', 'oss', 'French - French (alt.)'),
        ('fr', 'bepo', 'French - French (Bepo)'),
    ]


def test_apply_locale_fills_the_recipe() -> None:
    """Locale and keyboard reach the fisherman recipe."""
    m = _load()
    recipe: dict[str, YamlValue] = {}
    m.apply_locale(
        recipe, {
            'locale': 'fr_FR.UTF-8',
            'keyboard': {
                'layout': 'fr',
                'variant': 'oss'
            }
        }
    )
    assert recipe == {
        'locale': 'fr_FR.UTF-8',
        'keyboard': {
            'model': 'pc105',
            'layout': 'fr',
            'variant': 'oss'
        }
    }


def test_apply_locale_ignores_missing_or_invalid_choices() -> None:
    """A skipped step or an invalid value leaves the image default."""
    m = _load()
    choices: list[Mapping[str, YamlValue] | None] = [
        None, {}, {
            'locale': ''
        }, {
            'locale': 'x\ny'
        }, {
            'keyboard': {
                'layout': 'a b'
            }
        }, {
            'keyboard': None
        }, {
            'keyboard': {}
        }, {
            'keyboard': {
                'layout': ''
            }
        }, {
            'keyboard': {
                'layout': 3
            }
        }
    ]
    for system in choices:
        recipe: dict[str, YamlValue] = {}
        m.apply_locale(recipe, system)
        assert recipe == {}, system


def test_installer_and_fisherman_agree_on_the_keys() -> None:
    """Keys written by the installer are the ones fisherman reads and writes."""
    installer = (INSTALLER / 'utils' / 'locale_config.py').read_text()
    assert 'recipe["locale"]' in installer
    assert 'recipe["keyboard"]' in installer
    recipe_go = (FISHERMAN / 'internal' / 'recipe' /
                 'recipe.go.patch').read_text()
    assert 'json:"locale,omitempty"' in recipe_go
    assert 'json:"keyboard,omitempty"' in recipe_go
    for key in ('model', 'layout', 'variant'):
        assert f'json:"{key}' in recipe_go
    post = (FISHERMAN / 'internal' / 'post' / 'locale.go').read_text()
    for path in ('"locale.gen"', '"locale"', '"keyboard"'):
        assert path in post


def test_processor_applies_the_locale_and_the_module_is_installed() -> None:
    """The processor calls ``apply_locale`` and meson installs the module."""
    processor = (INSTALLER / 'utils' / 'processor.py.patch').read_text()
    assert (
        '+from bootc_installer.utils.locale_config import apply_locale'
        in processor
    )
    assert '+        apply_locale(recipe, merged.get("system"))' in processor
    meson = (INSTALLER / 'utils' / 'meson.build.patch').read_text()
    assert "+  'locale_config.py'," in meson


def test_step_widgets_exist_in_the_template() -> None:
    """Every widget the step reads is declared in the blueprint."""
    blp = (INSTALLER / 'gtk' / 'default-system.blp').read_text()
    code = (INSTALLER / 'defaults' / 'system.py').read_text()
    children: list[str] = re.findall(r'(\w+) = Gtk\.Template\.Child\(\)', code)
    assert {'locale_group', 'locale_row', 'keyboard_row'} <= set(children)
    for name in children:
        assert re.search(rf'\b{name}\b', blp), name


def test_loader_guard_rejects_a_module_without_the_surface(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The loader refuses a module that lacks the tested helpers.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(sys.modules[__name__], 'load_module', bare_loader)
    with pytest.raises(TypeError, match='lacks its test surface'):
        _ = _load()
