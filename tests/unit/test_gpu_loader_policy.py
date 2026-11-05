"""Unit tests of the GPU loader-policy modprobe confs.

The knob set the owner validated on the PVE host (04/11): the GSP-off knob
travels INSIDE the debs (``options nvidia NVreg_EnableGpuFirmware=0`` in both
-nvidia policy confs), never as a host tweak — assert the conf payload.
"""

from pathlib import Path

POLICY_DIR = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'kernel' / 'modules' / 'gpu' / 'modprobe'
)
SET_POLICY = {
    'dc-gpu-ia-nvidia.conf': 'ia',
    'dc-gpu-gaming-nvidia.conf': 'gaming',
}


def read_policy(name: str) -> str:
    """Read a lane modprobe policy conf.

    Args:
        name: Conf file name.

    Returns:
        The file content.
    """
    return (POLICY_DIR / name).read_text(encoding='utf-8')


def test_nvidia_policy_confs_disable_gsp() -> None:
    """Both -nvidia set confs carry the GSP-off knob (owner 04/11)."""
    for name in SET_POLICY:
        lines = read_policy(name).splitlines()
        knob = [
            line for line in lines
            if line.startswith('options nvidia NVreg_EnableGpuFirmware=')
        ]
        expected = [
            'options nvidia NVreg_EnableGpuFirmware=0 '
            'NVreg_RegistryDwords=RMInstLoc2=0x00000001'
        ] if name == 'dc-gpu-ia-nvidia.conf' else [
            'options nvidia NVreg_EnableGpuFirmware=0'
        ]
        assert knob == expected, (
            f'{name}: the GSP-off/VRAM knobs are '
            'missing or altered (IA carries RMInstLoc2, '
            'gaming does not)'
        )


def test_nvidia_policy_confs_keep_the_knob_in_one_place() -> None:
    """One knob declaration per conf.

    A duplicate line would make the option application order ambiguous for the
    gaming policy that shares the module with the modeset switch.
    """
    for name in SET_POLICY:
        knobs = [
            line for line in read_policy(name).splitlines()
            if 'NVreg_EnableGpuFirmware' in line
        ]
        assert len(knobs) == 1, f'{name}: {len(knobs)} GSP knob lines'


def test_gaming_policy_keeps_its_modeset() -> None:
    """The gaming policy still activates the nvidia_drm KMS modeset."""
    assert 'options nvidia-drm modeset=1' in read_policy(
        'dc-gpu-gaming-nvidia.conf'
    ).splitlines()


def test_both_policies_blacklist_nouveau() -> None:
    """Both -nvidia policies still push nouveau away from the device."""
    for name in SET_POLICY:
        assert 'blacklist nouveau' in read_policy(name).splitlines()
