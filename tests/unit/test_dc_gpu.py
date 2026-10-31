"""Unit tests for ``dc-gpu``, run against a sandbox root and a fake sysfs."""

import os
import shutil
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
        DC_GPU_LDCONFIG='true',
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


@pytest.mark.parametrize(
    'containerfile', ['Containerfile', 'Containerfile.minimal']
)
def test_dc_gpu_ships_in_the_images(containerfile: str) -> None:
    """Every image copies ``src/basepostinstall`` and the script is executable.

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
        [
            'git', '-C',
            str(root), 'ls-files', '-s',
            str(SCRIPT.relative_to(root))
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()[0]
    assert mode == '100755'


def payload(tmp_path: Path, profile: str, rusticl: bool = False) -> Path:
    """Create a fake installed userspace build for a profile.

    Args:
        tmp_path: Sandbox directory.
        profile: Profile name (directory under the build prefix).
        rusticl: Whether the build ships an OpenCL ICD.

    Returns:
        The sandbox path of the profile data directory.
    """
    root = tmp_path / 'root'
    lib = root / 'usr' / 'lib' / 'dc-gpu' / profile / 'lib'
    share = root / 'usr' / 'share' / 'dc-gpu' / profile
    (lib / 'dri').mkdir(parents=True)
    (share / 'vulkan' / 'icd.d').mkdir(parents=True)
    (share / 'glvnd' / 'egl_vendor.d').mkdir(parents=True)
    (share / 'vulkan' / 'icd.d' / 'radeon.json').write_text('{}')
    if rusticl:
        vendors = share / 'etc' / 'OpenCL' / 'vendors'
        vendors.mkdir(parents=True)
        (vendors / 'rusticl.icd').write_text('libRusticlOpenCL.so.1\n')
    return share


def read(tmp_path: Path, rel: str) -> str:
    """Read a file of the sandbox root.

    Args:
        tmp_path: Sandbox directory.
        rel: Path below the sandbox root.

    Returns:
        The file content.
    """
    return (tmp_path / 'root' / rel).read_text(encoding='utf-8')


@pytest.mark.parametrize('profile', ['gaming', 'ia'])
def test_set_activates_the_profile_prefix(tmp_path: Path, profile: str) -> None:
    """Each profile points the linker and the loaders at its own prefix.

    Args:
        tmp_path: Sandbox directory.
        profile: The profile under test.
    """
    for name in ('gaming', 'ia'):
        payload(tmp_path, name)
    assert run(tmp_path, 'set', profile).returncode == 0
    prefix = f'/usr/lib/dc-gpu/{profile}'
    assert read(tmp_path, 'etc/ld.so.conf.d/dc-gpu.conf') == f'{prefix}/lib\n'
    env = read(tmp_path, 'etc/environment.d/50-dc-gpu.conf')
    assert (
        f'VK_DRIVER_FILES=/usr/share/dc-gpu/{profile}/vulkan/icd.d/radeon.json'
        in env
    )
    assert f'LIBGL_DRIVERS_PATH={prefix}/lib/dri' in env
    assert (
        f'__EGL_VENDOR_LIBRARY_DIRS=/usr/share/dc-gpu/{profile}/'
        'glvnd/egl_vendor.d' in env
    )
    other = 'ia' if profile == 'gaming' else 'gaming'
    assert f'dc-gpu/{other}' not in env
    assert f'userspace: {profile}' in run(tmp_path, 'status').stdout


def test_ia_build_exposes_its_opencl_icd(tmp_path: Path) -> None:
    """A build shipping an OpenCL ICD is merged with the host ICDs.

    Args:
        tmp_path: Sandbox directory.
    """
    payload(tmp_path, 'ia', rusticl=True)
    host = tmp_path / 'root' / 'etc' / 'OpenCL' / 'vendors'
    host.mkdir(parents=True)
    (host / 'amdocl64.icd').write_text('libamdocl64.so\n')
    assert run(tmp_path, 'set', 'ia').returncode == 0
    env = read(tmp_path, 'etc/environment.d/50-dc-gpu.conf')
    assert 'OCL_ICD_VENDORS=/etc/dc-gpu/OpenCL/vendors' in env
    merged = tmp_path / 'root' / 'etc' / 'dc-gpu' / 'OpenCL' / 'vendors'
    assert sorted(p.name
                  for p in merged.iterdir()) == ['amdocl64.icd', 'rusticl.icd']


def test_gaming_build_without_opencl_leaves_the_host_loader(
    tmp_path: Path
) -> None:
    """No OpenCL variable is set when the profile ships no ICD.

    Args:
        tmp_path: Sandbox directory.
    """
    payload(tmp_path, 'gaming')
    assert run(tmp_path, 'set', 'gaming').returncode == 0
    env = read(tmp_path, 'etc/environment.d/50-dc-gpu.conf')
    assert 'OCL_ICD_VENDORS' not in env


def test_host_vulkan_icds_stay_visible(tmp_path: Path) -> None:
    """The loader's default search is replaced, so host ICDs are listed too.

    Args:
        tmp_path: Sandbox directory.
    """
    payload(tmp_path, 'gaming')
    host = tmp_path / 'root' / 'usr' / 'share' / 'vulkan' / 'icd.d'
    host.mkdir(parents=True)
    (host / 'nvidia_icd.json').write_text('{}')
    assert run(tmp_path, 'set', 'gaming').returncode == 0
    env = read(tmp_path, 'etc/environment.d/50-dc-gpu.conf')
    assert '/usr/share/vulkan/icd.d/nvidia_icd.json' in env


def test_auto_follows_the_connected_display(tmp_path: Path) -> None:
    """Auto picks gaming with a connected display, ia on a headless host.

    Args:
        tmp_path: Sandbox directory.
    """
    for name in ('gaming', 'ia'):
        payload(tmp_path, name)
    assert run(tmp_path, 'set', 'auto').returncode == 0
    assert 'userspace: ia' in run(tmp_path, 'status').stdout
    out = tmp_path / 'drm' / 'card0-HDMI-A-1'
    out.mkdir(parents=True)
    (out / 'status').write_text('connected\n')
    assert run(tmp_path, 'apply').returncode == 0
    assert 'userspace: gaming' in run(tmp_path, 'status').stdout


def test_missing_build_clears_the_activation(tmp_path: Path) -> None:
    """Without the profile's build the system libraries stay active.

    Args:
        tmp_path: Sandbox directory.
    """
    payload(tmp_path, 'gaming')
    assert run(tmp_path, 'set', 'gaming').returncode == 0
    shutil.rmtree(tmp_path / 'root' / 'usr' / 'lib' / 'dc-gpu')
    result = run(tmp_path, 'apply')
    assert result.returncode == 0
    assert 'not installed' in result.stderr
    conf = tmp_path / 'root' / 'etc' / 'ld.so.conf.d' / 'dc-gpu.conf'
    assert not conf.exists()
    assert 'userspace: none' in run(tmp_path, 'status').stdout
