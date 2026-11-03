"""Static consistency checks of the ``packages.yml`` manifest."""

import json
import os
import re
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
    assert 'Package: ${KERNEL_PKG}/' in build
    assert 'KERNEL_PKG="daemoncores-kernel-' in build
    assert 'linux-image-minimal' in build
    assert 'Conflicts' in build
    assert 'Replaces' in build
    assert 'linux-image-stock' not in build
    assert 'linux-image-${DEB_ARCH}, linux-image-' not in build


def test_image_installs_the_project_kernel() -> None:
    """Containerfile installs the single project kernel."""
    root = MANIFEST.parents[2]
    kernel = 'linux-image-${KERNEL_VARIANT}${KERNEL_SUFFIX}-${ARCH}'
    for name in ('Containerfile', ):
        text = (root / name).read_text()
        install = [
            ln for ln in text.splitlines() if not ln.lstrip().startswith('#')
        ]
        assert any(kernel in ln for ln in install), name
        assert 'ARG KERNEL_VARIANT=minimal' in text, name
        assert not any('linux-image-${ARCH}' in ln for ln in install), name


def _install_lines(text: str) -> list[str]:
    """Return the non-comment lines of a Containerfile.

    Args:
        text: Containerfile content.

    Returns:
        Every line that is not a comment.
    """
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith('#')]


def test_image_installs_no_nvidia_or_foreign_arch_modules() -> None:
    """The standard image lists only the per-arch hardware modules.

    The NVIDIA open modules (`linux-modules-nvidia`) live in the separate
    NVIDIA image only.
    """
    root = MANIFEST.parents[2]
    modules = {}
    for name in ('Containerfile', ):
        modules[name] = {
            tok
            for ln in _install_lines((root / name).read_text())
            for tok in ln.replace(';', ' ').replace('\\', ' ').split()
            if tok.startswith('linux-modules-')
        }
    assert 'linux-modules-nvidia' not in modules['Containerfile']
    assert not any(
        'x86' in tok or 'modules-arm' in tok for tok in modules['Containerfile']
    ), modules


def test_nvidia_stack_is_only_in_the_nvidia_image() -> None:
    """The proprietary stack is a separate, amd64-only, licensed image."""
    root = MANIFEST.parents[2]
    standard = '\n'.join(_install_lines((root / 'Containerfile').read_text()))
    for token in ('linux-modules-nvidia', 'nvidia-driver-libs', 'libcuda1'):
        assert token not in standard, token
    text = (root / 'Containerfile.nvidia').read_text()
    install = '\n'.join(_install_lines(text))
    assert 'FROM ${BASE_IMAGE}' in install
    assert 'linux-modules-nvidia' in install
    assert 'libcuda1' in install
    assert 'LABEL org.daemoncores.arches="amd64"' in install
    assert 'LABEL org.daemoncores.requires-eula="nvidia"' in install


def test_standard_image_keeps_the_login_stack() -> None:
    """The login and console packages are installed on the image's tree.

    They live in the shared socle of Containerfile.base: asserting over the
    base as well is enough, the standard image inherits whatever layer of
    the chain installs them.
    """
    root = MANIFEST.parents[2]
    text = (root / 'Containerfile').read_text()
    base = (root / 'Containerfile.base').read_text()
    for pkg in (
        'systemd-sysv', 'libpam-systemd', 'dbus-user-session', 'kbd',
        'keyboard-configuration'
    ):
        assert pkg in text or pkg in base, pkg
    for pkg in (
        'systemd-sysv', 'libpam-systemd', 'dbus-user-session', 'kbd',
        'keyboard-configuration'
    ):
        line = f'        {pkg} \\' if pkg in text else f'        {pkg}'
        assert line in text or line in base, pkg


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
    assert set(variants) == {'', '-16k'}
    assert entry['env']['KERNEL_PAGES'] == '4k'
    assert variants['-16k']['env']['KERNEL_PAGES'] == '16k'
    assert variants['-16k']['when'] == {'arch': 'arm64'}
    assert 'when' not in entry
    root = (
        MANIFEST.parents[2].parent / 'DaemonCores-CI' / 'build-deb' /
        'kernel-shared' / 'pages'
    )
    if not root.is_dir():
        return
    assert 'CONFIG_ARM64_4K_PAGES=y' in (root / '4k').read_text()
    assert 'CONFIG_ARM64_16K_PAGES=y' in (root / '16k').read_text()
    assert 'CONFIG_LOCALVERSION="-16k"' in (root / '16k').read_text()


def test_each_arm_module_follows_its_kernel() -> None:
    """Older devices build against the 4 KB kernel, recent ones the 16 KB."""
    devices = _variants('linux-modules-arm-device')
    for old in ('rpi3', 'rpi4', 'rk3399', 'h616', 'imx8m', 'mt8183'):
        assert devices[old]['deps'] == ['linux-image'], old
        assert 'env' not in devices[old], old
    for recent in ('rpi5', 'rk3588', 'rk3566'):
        assert devices[recent]['deps'] == ['linux-image-16k'], recent
        assert devices[recent]['env'] == {'KERNEL_SUFFIX': '-16k'}, recent


def test_every_arm_family_has_a_variant_and_a_fragment() -> None:
    """Each device module variant carries its kernel/modules/<SoC> fragment.

    One fragment per SoC family, not per board: the rpi3 fragment covers
    BCM2710A1 (Pi Zero 2 W), rk3566 covers the RK356x, h616 covers the sun50i
    family. A variant without its overlay file would make the CI build fail
    the "overlay missing" check at first build. The fragments are engine data
    (DaemonCores-CI build-deb/kernel-shared/modules) — skipped when the
    sibling engine checkout is not present locally.
    """
    devices = _variants('linux-modules-arm-device')
    overlays = (
        MANIFEST.parents[2].parent / 'DaemonCores-CI' / 'build-deb' /
        'kernel-shared' / 'modules'
    )
    if not overlays.is_dir():
        return
    for device in devices:
        overlay = overlays / device
        assert overlay.is_file(), device
        text = overlay.read_text()
        assert 'CONFIG_' in text, f'{device}: fragment carries no config'
        # The built-in SoC platform core is stated in every fragment.
        assert re.search(r'^CONFIG_ARCH_\w+=y', text, re.M), device


def test_there_is_no_unsigned_twin_anymore() -> None:
    """L1: one kernel per (arch, page size); enforcement is not a variant."""
    variants = _variants('linux-image')
    assert '-nosign' not in variants
    assert '-16k-nosign' not in variants
    # The enforcement is decided at install (module.sig_enforce=1 karg), so the
    # kernel itself is built without MODULE_SIG_FORCE.
    assert _packages()['linux-image']['env']['KERNEL_SIGNING_ENFORCE'] == 'no'
    assert 'unsigned-kernel' not in (
        variants[''].get('when') or variants['-16k'].get('when') or {}
    )


def test_kernel_build_provides_the_signed_names() -> None:
    """The kernel Provides the names the images and modules install by."""
    build = _packages()['linux-image']['build']
    assert 'linux-image-minimal${KERNEL_SUFFIX:-}-${DEB_ARCH}' in build
    assert 'OTHER_PKG' not in build
    assert 'daemoncores-kernel-${ORIG_PKG#linux-image-}' in build


def test_the_installer_carries_the_enforcement_switch() -> None:
    """The bootc-installer writes module.sig_enforce=1 by default."""
    fisherman = (
        MANIFEST.parents[1] / 'bootc-debs-builder' / 'fisherman-src' /
        'fisherman' / 'internal' / 'recipe' / 'recipe.go.patch'
    ).read_text()
    assert 'module.sig_enforce=1' in fisherman


def test_the_boot_manifest_has_no_nosign_category_suffix() -> None:
    """The categories choose enforcement via kargs, not by kernel package."""
    tests = MANIFEST.parents[1] / 'tests.yml'
    text = tests.read_text()
    assert 'kargs: ["module.sig_enforce=1"]' in text
    assert '-nosign' not in text
    assert 'unsigned-kernel' not in str(
        _variants('linux-image')['-16k'].get('when', {})
    )


def test_unsigned_kernel_provides_the_signed_name_for_the_modules() -> None:
    """The kernel Provides the names the images and modules install by."""
    build = _packages()['linux-image']['build']
    assert 'linux-image-minimal${KERNEL_SUFFIX:-}-${DEB_ARCH}' in build
    assert 'daemoncores-kernel-${ORIG_PKG#linux-image-}' in build
    assert 'OTHER_PKG' not in build


def test_images_build_on_the_shared_base() -> None:
    """The image starts from the base and installs the kernel in its own RUN."""
    root = MANIFEST.parents[2]
    base = (root / 'Containerfile.base').read_text()
    assert 'FROM debian:trixie' in base
    assert 'KERNEL_SUFFIX' not in base
    for name in ('Containerfile', ):
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
