"""Unit tests for ``dc-gpu``, run against a sandbox root and a fake sysfs."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'src' / 'basepostinstall' / 'usr' /
    'sbin' / 'dc-gpu'
)


def run(
    tmp_path: Path, *args: str, vendors: tuple[str, ...] = ()
) -> subprocess.CompletedProcess:
    """Run the real script with a sandbox root and fake DRM devices.

    Args:
        tmp_path: Sandbox directory.
        *args: Command line of the script.
        vendors: PCI vendor ids (hex) of the fake display devices.

    Returns:
        The completed process.
    """
    drm = tmp_path / 'drm'
    for idx, vendor in enumerate(vendors):
        dev = drm / f'card{idx}' / 'device'
        dev.mkdir(parents=True, exist_ok=True)
        (dev / 'vendor').write_text(vendor + '\n', encoding='utf-8')
    drm.mkdir(exist_ok=True)
    env = dict(
        os.environ,
        INSTALL_ROOT=str(tmp_path / 'root'),
        DC_GPU_SYSFS=str(drm),
    )
    return subprocess.run(
        ['sh', str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def modload(tmp_path: Path) -> str:
    """Read the generated modules-load fragment.

    Args:
        tmp_path: Sandbox directory.

    Returns:
        The fragment content.
    """
    return (tmp_path / 'root' / 'etc' / 'modules-load.d' /
            'dc-gpu.conf').read_text(encoding='utf-8')


def test_status_defaults_to_auto_and_lists_vendors(tmp_path: Path) -> None:
    """Without a stored profile the status reports auto and each vendor.

    Args:
        tmp_path: Sandbox directory.
    """
    result = run(tmp_path, 'status', vendors=('0x1002', '0x10de'))
    assert result.returncode == 0, result.stderr
    assert 'profile: auto' in result.stdout
    assert 'vendors: amd nvidia' in result.stdout
    assert 'nvidia-consent: no' in result.stdout


def test_set_records_profile(tmp_path: Path) -> None:
    """``set`` stores the profile and ``status`` reads it back.

    Args:
        tmp_path: Sandbox directory.
    """
    assert run(tmp_path, 'set', 'gaming').returncode == 0
    assert 'profile: gaming' in run(tmp_path, 'status').stdout


def test_ia_without_consent_loads_no_nvidia_module(tmp_path: Path) -> None:
    """NVIDIA userspace stays off until the install consent exists.

    Args:
        tmp_path: Sandbox directory.
    """
    assert run(tmp_path, 'set', 'ia', vendors=('0x10de', )).returncode == 0
    assert 'nvidia' not in modload(tmp_path).replace('dc-gpu', '')


def test_ia_with_consent_loads_nvidia_modules(tmp_path: Path) -> None:
    """With consent and an NVIDIA device the compute modules are loaded.

    Args:
        tmp_path: Sandbox directory.
    """
    conf = tmp_path / 'root' / 'etc' / 'dc-gpu'
    conf.mkdir(parents=True)
    (conf / 'nvidia-consent').write_text('accepted-at-install\n')
    assert run(tmp_path, 'set', 'ia', vendors=('0x10de', )).returncode == 0
    assert 'nvidia_uvm' in modload(tmp_path)


def test_ia_on_amd_needs_nothing_from_nvidia(tmp_path: Path) -> None:
    """The ia profile works on a machine without NVIDIA hardware.

    Args:
        tmp_path: Sandbox directory.
    """
    assert run(tmp_path, 'set', 'ia', vendors=('0x1002', )).returncode == 0
    assert 'nvidia_' not in modload(tmp_path)


def test_gaming_never_loads_nvidia_compute(tmp_path: Path) -> None:
    """The gaming profile keeps NVIDIA on the in-tree driver.

    Args:
        tmp_path: Sandbox directory.
    """
    conf = tmp_path / 'root' / 'etc' / 'dc-gpu'
    conf.mkdir(parents=True)
    (conf / 'nvidia-consent').write_text('accepted-at-install\n')
    assert run(tmp_path, 'set', 'gaming', vendors=('0x10de', )).returncode == 0
    assert 'nvidia_uvm' not in modload(tmp_path)


@pytest.mark.parametrize('args', [(), ('set', ), ('set', 'evil'), ('bogus', )])
def test_usage_errors(tmp_path: Path, args: tuple[str, ...]) -> None:
    """Bad command lines exit with status 2.

    Args:
        tmp_path: Sandbox directory.
        args: The invalid command line.
    """
    assert run(tmp_path, *args).returncode == 2


@pytest.mark.parametrize('containerfile', ['Containerfile', 'Containerfile.minimal'])
def test_dc_gpu_ships_in_the_images(containerfile: str) -> None:
    """Every image copies ``src/basepostinstall`` to ``/`` and the script is executable.

    Args:
        containerfile: Containerfile that must carry the script.
    """
    root = SCRIPT.parents[4]
    text = (root / containerfile).read_text()
    assert any(
        line.split() == ['COPY', './src/basepostinstall', '/']
        for line in text.splitlines()
    )
    mode = subprocess.run(
        ['git', '-C', str(root), 'ls-files', '-s', str(SCRIPT.relative_to(root))],
        capture_output=True, text=True, check=True,
    ).stdout.split()[0]
    assert mode == '100755'
