"""Static consistency checks of the ``packages.yml`` manifest."""

import json
import os
import shutil
import subprocess
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
    assert 'PKG_NAME="${KERNEL_PKG}"' in build
    assert 'KERNEL_PKG="daemoncores-kernel-' in build
    provides = 'PROVIDES="linux-image-minimal${KERNEL_SUFFIX:-}-${DEB_ARCH}"'
    assert provides in build
    assert 'linux-image-stock' not in build
    assert 'linux-image-${DEB_ARCH}, linux-image-' not in build


def test_both_images_install_the_same_project_kernel() -> None:
    """Containerfile and Containerfile.minimal install the single kernel."""
    root = MANIFEST.parents[2]
    kernel = 'linux-image-${KERNEL_VARIANT}${KERNEL_SUFFIX}-${ARCH}'
    for name in ('Containerfile', 'Containerfile.minimal'):
        text = (root / name).read_text()
        install = [
            ln for ln in text.splitlines() if not ln.lstrip().startswith('#')
        ]
        assert any(kernel in ln for ln in install), name
        assert 'ARG KERNEL_VARIANT=minimal' in text, name
        assert not any('linux-image-${ARCH}' in ln for ln in install), name


def test_both_images_install_the_same_modules() -> None:
    """The standard image keeps the hardware support of the minimal one.

    The standard image additionally carries the NVIDIA open modules
    (`linux-modules-nvidia`, amd64 only); the minimal image has no GPU stack.
    """
    root = MANIFEST.parents[2]
    modules = {}
    for name in ('Containerfile', 'Containerfile.minimal'):
        text = (root / name).read_text()
        modules[name] = {
            tok
            for ln in text.splitlines() if not ln.lstrip().startswith('#')
            for tok in ln.replace(';', ' ').replace('\\', ' ').split()
            if tok.startswith('linux-modules-')
        }
    gpu_extra = {'linux-modules-nvidia'}
    assert modules['Containerfile'] - gpu_extra \
        == modules['Containerfile.minimal']
    assert not any(
        'x86' in tok or 'modules-arm' in tok for tok in modules['Containerfile']
    ), modules


def test_standard_image_keeps_the_login_stack() -> None:
    """The login and console packages are installed explicitly."""
    text = (MANIFEST.parents[2] / 'Containerfile').read_text()
    for pkg in (
        'systemd-sysv', 'libpam-systemd', 'dbus-user-session', 'kbd',
        'keyboard-configuration'
    ):
        assert f'        {pkg} \\' in text, pkg


def _variants(name: str) -> dict[str, Any]:
    """Return the ``variants`` mapping of a manifest template.

    Args:
        name: Name of a package entry that declares ``variants``.

    Returns:
        The variant overrides keyed by variant key.
    """
    return cast(dict[str, Any], _packages()[name]['variants'])


def test_arm64_has_a_4k_and_a_16k_kernel() -> None:
    """The kernel entry builds a 4 KB kernel and an arm64-only 16 KB one."""
    entry = _packages()['linux-image']
    variants = _variants('linux-image')
    assert set(variants) == {'', '-16k', '-nosign', '-16k-nosign'}
    assert entry['env']['KERNEL_PAGES'] == '4k'
    assert variants['-16k']['env']['KERNEL_PAGES'] == '16k'
    assert variants['-16k']['when'] == {'arch': 'arm64'}
    assert 'when' not in entry
    root = MANIFEST.parent / 'kernel' / 'pages'
    assert 'CONFIG_ARM64_4K_PAGES=y' in (root / '4k').read_text()
    assert 'CONFIG_ARM64_16K_PAGES=y' in (root / '16k').read_text()
    assert 'CONFIG_LOCALVERSION="-16k"' in (root / '16k').read_text()


def test_each_arm_module_follows_its_kernel() -> None:
    """Older devices build against the 4 KB kernel, recent ones the 16 KB."""
    devices = _variants('linux-modules-arm-device')
    for old in ('rpi3', 'rpi4'):
        assert devices[old]['deps'] == ['linux-image'], old
        assert 'env' not in devices[old], old
    for recent in ('rpi5', 'rk3588'):
        assert devices[recent]['deps'] == ['linux-image-16k'], recent
        assert devices[recent]['env'] == {'KERNEL_SUFFIX': '-16k'}, recent


def test_only_the_generic_kernels_have_an_unsigned_twin() -> None:
    """The unsigned kernel exists for amd64 and the 16 KB arm64 kernel only."""
    variants = _variants('linux-image')
    for key, arch, pages in (('-nosign', 'amd64', None),
                             ('-16k-nosign', 'arm64', '16k')):
        variant = variants[key]
        assert variant['when'] == {'arch': arch, 'unsigned-kernel': True}, key
        assert variant['env']['KERNEL_SIGNING_ENFORCE'] == 'no', key
        assert variant['deb-glob'] == f'linux-image-common{key}_*', key
        assert variant['env'].get('KERNEL_PAGES') == pages, key
    assert 'KERNEL_SIGNING_ENFORCE' not in variants['-16k'].get('env', {})


def test_unsigned_kernel_provides_the_signed_name_for_the_modules() -> None:
    """The twin Provides the signed name the device modules Depend on."""
    build = _packages()['linux-image']['build']
    assert 'PROVIDES="${PROVIDES}, ${KERNEL_PKG} (= ${BUILT_VER})"' in build
    assert 'Conflicts: %s, %s, linux-image-%s' in build


def test_images_build_on_the_shared_base() -> None:
    """Both images start from the base and install the kernel in its own RUN."""
    root = MANIFEST.parents[2]
    base = (root / 'Containerfile.base').read_text()
    assert 'FROM debian:trixie' in base
    assert 'KERNEL_SUFFIX' not in base
    for name in ('Containerfile', 'Containerfile.minimal'):
        text = (root / name).read_text()
        assert 'FROM ${BASE_IMAGE}' in text, name
        assert 'FROM debian:trixie' not in text, name
        suffix = text.index('ARG KERNEL_SUFFIX')
        assert text.index(
            '        linux-image-${KERNEL_VARIANT}'
        ) > suffix, name
        assert 'bootcpreinstall' not in text, name


def _expand(arch: str) -> list[dict[str, Any]]:
    """Expand the manifest variants with the shared ``expand.jq`` filter.

    Args:
        arch: Target architecture kept by the filter.

    Returns:
        The resolved package entries.
    """
    assert shutil.which('jq'), 'jq is required to expand the manifest'
    ci_repo = Path(os.environ.get('CI_REPO', str(MANIFEST.parents[2] / '.ci')))
    data = yaml.safe_load(MANIFEST.read_text())
    done = subprocess.run(
        ['jq', '-c', '-f',
         str(ci_repo / 'manifest-expand' / 'expand.jq')],
        input=json.dumps(data),
        env=dict(os.environ, ARCH=arch),
        capture_output=True,
        text=True,
        check=True,
    )
    return cast(list[dict[str, Any]], json.loads(done.stdout)['packages'])


def test_gpu_userspace_expands_to_both_profiles_at_every_level() -> None:
    """Each profile expands to one package per CPU level of its arch."""
    amd64 = {p['name']: p for p in _expand('amd64')}
    arm64 = {p['name'] for p in _expand('arm64')}
    for profile in ('gaming', 'ia'):
        for level in ('x64v1', 'x64v2', 'x64v3'):
            entry = amd64[f'gpu-userspace-{profile}-{level}']
            assert entry['env']['GPU_PROFILE'] == profile
            assert entry['env']['GPU_LEVEL'] == level
            assert entry['env']['GPU_VARIANT'] == f'{profile}-{level}'
            assert 'gpu-userspace' in entry['sources']
        assert f'gpu-userspace-{profile}-generic' in arm64
        assert f'gpu-userspace-{profile}-generic' not in amd64
        assert not any(f'gpu-userspace-{profile}-x64' in n for n in arm64)


def test_gpu_userspace_lists_no_vendor_and_no_fixed_march() -> None:
    """Drivers stay on auto and the CPU level comes from the variable."""
    build = _packages()['gpu-userspace']['build']
    code = '\n'.join(
        ln for ln in build.splitlines() if not ln.lstrip().startswith('#')
    )
    assert '-Dgallium-drivers=auto' in code
    assert '-Dvulkan-drivers=auto' in code
    for vendor in ('radeonsi', 'iris', 'nouveau', 'panfrost'):
        assert vendor not in code, vendor
    assert 'kernel_flavour_kcflags "${GPU_LEVEL}"' in code
    assert '-march' not in code
