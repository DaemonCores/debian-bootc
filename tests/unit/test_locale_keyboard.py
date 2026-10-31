"""Language and keyboard choices of the installer ``system`` step."""

import re
import types
from pathlib import Path
from typing import Any

BUILDER = Path(__file__
               ).resolve().parents[2] / 'workflows' / 'bootc-debs-builder'
INSTALLER = BUILDER / 'bootc-installer-src' / 'bootc_installer'
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

! option
  grp             Switching to another layout
"""


def _module() -> types.ModuleType:
    """Load ``locale_config.py`` straight from the installer overlay.

    Returns:
        The module, executed without any GTK dependency.
    """
    path = INSTALLER / 'utils' / 'locale_config.py'
    module = types.ModuleType('locale_config')
    exec(compile(path.read_text(), path.name, 'exec'), module.__dict__)
    return module


def test_locale_validation() -> None:
    """Only a glibc name with a charset passes."""
    m = _module()
    for good in ('fr_FR.UTF-8', 'eo.UTF-8', 'sr_RS.UTF-8@latin', 'C.UTF-8'):
        assert m.valid_locale(good), good
    for bad in (
        '', 'fr_FR', 'fr_FR.UTF-8\nLANG=C', 'fr FR.UTF-8', '../x.UTF-8'
    ):
        assert not m.valid_locale(bad), bad


def test_keyboard_validation() -> None:
    """Layout and model are XKB names, the variant may be empty."""
    m = _module()
    assert m.valid_keyboard('fr', 'oss')
    assert m.valid_keyboard('us,fr', '')
    assert not m.valid_keyboard('', '')
    assert not m.valid_keyboard('us\nX=1', '')
    assert not m.valid_keyboard('us', 'a b')
    assert not m.valid_keyboard('us', '', model='')


def test_supported_locales_keeps_valid_utf8_entries(tmp_path: Path) -> None:
    """Non UTF-8 charsets, comments and malformed names are dropped."""
    m = _module()
    listing = tmp_path / 'SUPPORTED'
    listing.write_text(SUPPORTED)
    assert m.supported_locales(str(listing)) == [
        'en_US.UTF-8', 'eo.UTF-8', 'fr_FR.UTF-8', 'sr_RS.UTF-8@latin'
    ]


def test_missing_lists_give_no_choice(tmp_path: Path) -> None:
    """An unreadable list leaves the image default, without an error."""
    m = _module()
    assert m.supported_locales(str(tmp_path / 'none')) == []
    assert m.keyboard_layouts(str(tmp_path / 'none')) == []


def test_keyboard_layouts_join_variants_to_their_layout(tmp_path: Path) -> None:
    """Layouts and variants are listed together, sorted by description."""
    m = _module()
    listing = tmp_path / 'base.lst'
    listing.write_text(BASE_LST)
    assert m.keyboard_layouts(str(listing)) == [
        ('us', '', 'English (US)'),
        ('us', 'intl', 'English (US) - English (US, intl., with dead keys)'),
        ('fr', '', 'French'),
        ('fr', 'oss', 'French - French (alt.)'),
        ('fr', 'bepo', 'French - French (Bepo)'),
    ]


def test_apply_locale_fills_the_recipe() -> None:
    """Locale and keyboard reach the fisherman recipe."""
    m = _module()
    recipe: dict[str, Any] = {}
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
    m = _module()
    for system in (
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
        }
    ):
        recipe: dict[str, Any] = {}
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
    children = re.findall(r'(\w+) = Gtk\.Template\.Child\(\)', code)
    assert {'locale_group', 'locale_row', 'keyboard_row'} <= set(children)
    for name in children:
        assert re.search(rf'\b{name}\b', blp), name
