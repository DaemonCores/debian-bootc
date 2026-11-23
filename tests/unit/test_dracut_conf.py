"""The initramfs must carry a display driver, else the LUKS prompt is invisible.

``systemd-cryptsetup`` asks for the passphrase inside the initrd.  The dracut
config shipped in the image listed no KMS driver, so on a VM the screen stayed
frozen on the bootloader line and the boot looked hung (DEBUG.md item 24).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder'
DRACUT_CONF = (
    ROOT / 'bootcpostinstall' / 'usr' / 'lib' / 'dracut' / 'dracut.conf.d' /
    '30-bootc-build.conf'
)
KCONFIG = ROOT / 'kernel-src' / 'config.cfg'
# add_drivers name -> kernel symbol that builds it
SYMBOL = {
    'simpledrm': 'CONFIG_DRM_SIMPLEDRM',
    'bochs': 'CONFIG_DRM_BOCHS',
    'virtio_gpu': 'CONFIG_DRM_VIRTIO_GPU',
    'cirrus-qemu': 'CONFIG_DRM_CIRRUS_QEMU',
    'qxl': 'CONFIG_DRM_QXL',
    'vmwgfx': 'CONFIG_DRM_VMWGFX',
    'hyperv_drm': 'CONFIG_DRM_HYPERV',
}


def added_drivers() -> set[str]:
    """Collect every driver named by ``add_drivers`` in the dracut config.

    Returns:
        The driver names, across all ``add_drivers`` lines.
    """
    found: set[str] = set()
    for match in re.finditer(
        r'^add_drivers\+="([^"]*)"', DRACUT_CONF.read_text(), re.MULTILINE
    ):
        found.update(match.group(1).split())
    return found


def test_initrd_ships_a_kms_driver_for_vm_displays() -> None:
    """Every virtual display driver of SYMBOL is added to the initramfs."""
    missing = set(SYMBOL) - added_drivers()
    assert not missing, f'initrd has no display driver: {sorted(missing)}'


def test_added_display_drivers_exist_in_the_kernel_config() -> None:
    """A name dracut cannot find is skipped silently: tie it to a symbol."""
    kconfig = KCONFIG.read_text()
    for driver, symbol in SYMBOL.items():
        assert re.search(
            rf'^{symbol}=[my]\b', kconfig, re.MULTILINE
        ), f'{driver}: {symbol} is not enabled in kernel-src/config.cfg'
