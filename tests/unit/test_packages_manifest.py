"""Static consistency checks of the ``packages.yml`` manifest."""

from pathlib import Path
from typing import Any, cast

import yaml

MANIFEST = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'packages.yml'
)
GRUB_PINS = ('GRUB_VER', 'GRUB_FEDORA_BRANCH', 'GRUB_PINNED_COMMIT')


def _packages() -> dict[str, dict[str, Any]]:
    """Load the manifest entries keyed by package name.

    Returns:
        The ``packages.yml`` entries indexed by their ``name``.
    """
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))
    return {p['name']: p for p in data['packages']}


def test_grub_entries_share_the_same_pins() -> None:
    """amd64 and arm64 GRUB entries never ship different GRUB sources."""
    packages = _packages()
    amd64 = packages['grub-efi-amd64-signed']['env']
    arm64 = packages['grub-efi-arm64-signed']['env']
    for pin in GRUB_PINS:
        assert amd64[pin] == arm64[pin], pin
