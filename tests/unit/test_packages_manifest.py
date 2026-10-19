"""Static consistency checks of the ``packages.yml`` manifest."""

from pathlib import Path
from typing import Any, cast

import yaml

MANIFEST = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'packages.yml'
)
GRUB_PINS = ('GRUB_VER', 'GRUB_FEDORA_BRANCH', 'GRUB_PINNED_COMMIT')
GRUB_PACKAGES = ('grub-efi-amd64-signed', 'grub-efi-arm64-signed')


def _packages() -> dict[str, dict[str, Any]]:
    """Load the manifest entries keyed by package name.

    Returns:
        The ``packages.yml`` entries indexed by their ``name``.
    """
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))
    return {p['name']: p for p in data['packages']}


def test_grub_entries_follow_the_fedora_mainline() -> None:
    """Both GRUB entries track the rhboot/grub2 head and pin nothing."""
    packages = _packages()
    for name in GRUB_PACKAGES:
        entry = packages[name]
        assert entry['track']['GRUB_COMMIT'] == {
            'repo': 'rhboot/grub2',
            'head': True
        }, name
        for pin in GRUB_PINS:
            assert pin not in entry.get('env', {}), (name, pin)


def test_custom_kernel_does_not_masquerade_as_debian() -> None:
    """The project kernel has its own name and Provides only the minimal one."""
    lines = _packages()['linux-image']['build'].splitlines()
    build = '\n'.join(ln for ln in lines if not ln.lstrip().startswith('#'))
    assert 'Package: daemoncores-kernel-' in build
    assert 'Provides: linux-image-minimal-%s' in build
    assert 'linux-image-stock' not in build
    assert 'linux-image-${DEB_ARCH}, linux-image-' not in build


def test_standard_image_uses_the_debian_kernel() -> None:
    """The standard Containerfile installs linux-image-${ARCH}, no modules."""
    text = (MANIFEST.parents[2] / 'Containerfile').read_text()
    assert 'linux-image-${ARCH} \\' in text
    assert 'KERNEL_VARIANT' not in text
    install = [
        ln for ln in text.splitlines() if not ln.lstrip().startswith('#')
    ]
    assert not any('linux-modules-' in ln for ln in install)


def test_standard_image_keeps_the_login_stack() -> None:
    """The login and console packages are installed explicitly."""
    text = (MANIFEST.parents[2] / 'Containerfile').read_text()
    for pkg in (
        'systemd-sysv', 'libpam-systemd', 'dbus-user-session', 'kbd',
        'keyboard-configuration'
    ):
        assert f'        {pkg} \\' in text, pkg
