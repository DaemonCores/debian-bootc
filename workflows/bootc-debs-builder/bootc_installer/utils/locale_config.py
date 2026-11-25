"""Language and keyboard settings of the installer ``system`` step.

The system language and the keyboard layout are what the first-boot setup
service asked through ``dpkg-reconfigure``. They are chosen here from the lists
the live system ships (the glibc ``SUPPORTED`` file and the XKB rules list), so
nothing is hardcoded, and written by fisherman into ``/etc/default/locale``,
``/etc/locale.gen`` and ``/etc/default/keyboard`` of the installed system. The
helpers hold no GTK code so they can be tested alone.
"""

import re
from collections.abc import Mapping
from typing import TypeGuard

SUPPORTED_LOCALES = "/usr/share/i18n/SUPPORTED"
XKB_RULES_LIST = "/usr/share/X11/xkb/rules/base.lst"
# Generic 105-key PC keyboard, the Debian default model.
DEFAULT_MODEL = "pc105"

# Same shapes fisherman accepts: it refuses anything else, so a value that
# passes here is never rejected after the disk was already written.
LOCALE_RE = re.compile(
    r"^[A-Za-z]{1,3}(_[A-Za-z0-9]+)?\.[A-Za-z0-9-]+(@[A-Za-z0-9]+)?$"
)
XKB_TOKEN_RE = re.compile(r"^[A-Za-z0-9_]+(,[A-Za-z0-9_]+)*$")


def _is_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    """Tell whether a value is a mapping (a recipe or step dictionary).

    Args:
        value: Candidate value.

    Returns:
        True when the value is a mapping.
    """
    return isinstance(value, Mapping)


def valid_locale(locale: str) -> bool:
    """Tell whether a string is a glibc locale name with a charset.

    Args:
        locale: Candidate locale, such as ``fr_FR.UTF-8``.

    Returns:
        True when it has the ``language[_TERRITORY].charset[@modifier]`` shape.
    """
    return bool(LOCALE_RE.match(locale))


def valid_keyboard(
    layout: str, variant: str, model: str = DEFAULT_MODEL
) -> bool:
    """Tell whether the three XKB names are acceptable.

    Args:
        layout: XKB layout, such as ``fr``.
        variant: XKB variant, empty for the layout default.
        model: XKB model.

    Returns:
        True when the layout and the model are XKB names and the variant is
        empty or an XKB name.
    """
    return (
        bool(XKB_TOKEN_RE.match(layout)) and bool(XKB_TOKEN_RE.match(model))
        and (variant == "" or bool(XKB_TOKEN_RE.match(variant)))
    )


def supported_locales(path: str = SUPPORTED_LOCALES) -> list[str]:
    """List the UTF-8 locales the live system can generate.

    Args:
        path: glibc ``SUPPORTED`` file, lines ``fr_FR.UTF-8 UTF-8``.

    Returns:
        The sorted locale names, empty when the file cannot be read (the
        step then offers no choice and the image default stays).
    """
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    names: set[str] = set()
    for line in lines:
        fields = line.split()
        if (
            len(fields) == 2 and fields[1] == "UTF-8"
            and valid_locale(fields[0])
        ):
            names.add(fields[0])
    return sorted(names)


def keyboard_layouts(path: str = XKB_RULES_LIST) -> list[tuple[str, str, str]]:
    """List the keyboard layouts and variants of the XKB rules file.

    Args:
        path: XKB ``base.lst`` file made of ``! layout``, ``! variant`` and
            other sections.

    Returns:
        ``(layout, variant, description)`` tuples sorted by description; the
        variant is empty for the plain layout. Empty when the file cannot be
        read.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    layouts: dict[str, str] = {}
    variants: list[tuple[str, str, str]] = []
    section: str = ""
    for line in lines:
        if line.startswith("!"):
            section = line[1:].strip()
            continue
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        name, text = fields
        if section == "layout" and valid_keyboard(name, ""):
            layouts[name] = text
        elif section == "variant" and valid_keyboard("x", name):
            owner, _, description = text.partition(": ")
            if description:
                variants.append((owner, name, description))
    result: list[tuple[str, str, str]] = [(name, "", text)
                                          for name, text in layouts.items()]
    for owner, name, description in variants:
        if owner in layouts:
            result.append((owner, name, f"{layouts[owner]} - {description}"))
    return sorted(
        result, key=lambda item: (item[2].casefold(), item[0], item[1])
    )


def apply_locale(
    recipe: dict[str, object],
    system: Mapping[str, object] | None,
) -> None:
    """Merge the language and keyboard of the ``system`` step into a recipe.

    Args:
        recipe: Fisherman recipe being built, changed in place.
        system: The ``system`` entry of the merged finals, or None when the
            step was not shown. A missing or invalid choice leaves the
            image default untouched.
    """
    if not system:
        return
    locale = system.get("locale")
    if isinstance(locale, str) and valid_locale(locale):
        recipe["locale"] = locale
    keyboard = system.get("keyboard")
    if not _is_mapping(keyboard):
        return
    layout = keyboard.get("layout")
    if not isinstance(layout, str) or not layout:
        return
    model_value = keyboard.get("model")
    model = (
        model_value
        if isinstance(model_value, str) and model_value else DEFAULT_MODEL
    )
    variant_value = keyboard.get("variant")
    variant = variant_value if isinstance(variant_value, str) else ""
    if valid_keyboard(layout, variant, model):
        recipe["keyboard"] = {
            "model": model,
            "layout": layout,
            "variant": variant,
        }
