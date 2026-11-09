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
REPO = Path(__file__).resolve().parents[2]


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
    """The profile kernels own their name; Provides stay the minimal one."""
    lines = _packages()['linux-image-profile']['build'].splitlines()
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

    The NVIDIA open modules (`linux-modules-nvidia`) belong to the derived
    NVIDIA image at install only.
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


def test_nvidia_stack_is_not_a_hosted_image() -> None:
    """The proprietary stack lives in the derived lane, not a Containerfile."""
    root = MANIFEST.parents[2]
    standard = '\n'.join(_install_lines((root / 'Containerfile').read_text()))
    for token in ('linux-modules-nvidia', 'nvidia-driver-libs', 'libcuda1'):
        assert token not in standard, token
    # The separate NVIDIA image is retired (owner 03/11): the derived lane at
    # install replaces it. Nobody may recreate the hosted-image Containerfile.
    assert not (root / 'Containerfile.nvidia').exists()
    # The derived build carries the stack instead: the userspace list of
    # gpu-set-stage.py plus the FUSED set deb pinning (the NVIDIA release
    # rides the sibling set version's +r1nv suffix), behind the EULA label.
    stage = (
        root / 'src/buildisopreinstall/usr/libexec/debian-bootc/'
        'gpu-set-stage.py'
    ).read_text()
    assert 'nvidia-driver-libs' in stage
    assert 'libcuda1' in stage
    assert '+r1nv' in stage
    assert 'oset' in stage
    assert 'LABEL org.daemoncores.requires-eula="nvidia"' in stage


def test_standard_image_keeps_the_login_stack() -> None:
    """The login and console packages are installed on the image's tree.

    They live in the shared socle of Containerfile.base: asserting over the base
    as well is enough, the standard image inherits whatever layer of the chain
    installs them.
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
    """The page size is per ARCHITECTURE, inside the arch entries (owner 05/11).

    No separate 16k kernel entry and no generic baseline: the two profiles
    (ia, vm) x the 7 flavours (x64v1..v4 amd64, armv8.0 / armv8.2-lse /
    armv9-sve2 arm64) are the whole kernel estate. armv8.2-lse and
    armv9-sve2 default to 16 KB in-entry (Cortex-A76+ class, TLB-pressure
    gains); armv8.0 (Cortex-A53 class, no 16 KB granule) stays 4 KB
    automatically; x86 is trivially 4 KB everywhere.
    """
    entry = _packages()['linux-image-profile']
    variants = _variants('linux-image-profile')
    assert set(variants) == {
        f'{profile}-{flav}'
        for profile in ('ia', 'vm')
        for flav in (
            'x64v1', 'x64v2', 'x64v3', 'x64v4', 'armv8.0', 'armv8.2-lse',
            'armv9-sve2'
        )
    }
    # x64v4 = MANQUANT AJOUTÉ: present in BOTH profiles.
    for profile in ('ia', 'vm'):
        assert variants[f'{profile}-x64v4']['env']['KERNEL_ARCH_LEVEL'
                                                   ] == 'x64v4'
        assert variants[f'{profile}-x64v4']['when'] == {'arch': 'amd64'}
    # ENTRY-LEVEL default = 16 KB EVERYWHERE (owner 05/11 18:4x, amd64
    # included); the ONLY 4k redeclaration = the armv8.0 arch-incompatible
    # signal (no 16 KB granule); the x64 variants never redeclare a page
    # size (their fallback is architectural, x86 mainline has none).
    assert entry['env']['KERNEL_PAGES'] == '16k'
    for profile in ('ia', 'vm'):
        for flav in ('armv8.2-lse', 'armv9-sve2'):
            assert 'KERNEL_PAGES' not in variants[f'{profile}-{flav}']['env'], (
                f'{profile}-{flav}'
            )
            assert variants[f'{profile}-{flav}']['when'] == {'arch': 'arm64'}
        assert variants[f'{profile}-armv8.0']['env']['KERNEL_PAGES'] == '4k'
        assert variants[f'{profile}-armv8.0']['when'] == {'arch': 'arm64'}
        for flav in ('x64v1', 'x64v2', 'x64v3', 'x64v4'):
            assert 'KERNEL_PAGES' not in variants[f'{profile}-{flav}']['env']
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
    """Each device's kernel is picked by ARCHITECTURE class, never per device.

    A53/A72-class devices (Pi 3/4, RK3399, H616, i.MX8M, MT8183, RK356x) ride
    armv8.0 (4 KB automatically); A76-class devices (Pi 5, RK3588) ride
    armv8.2-lse (16 KB by default). No rpiN/rkM token appears in a kernel entry
    — the page size and the flavour are arch data, the device names live only in
    the module overlays.
    """
    devices = _variants('linux-modules-arm-device')
    for old in ('rpi3', 'rpi4', 'rk3399', 'h616', 'imx8m', 'mt8183', 'rk3566'):
        assert devices[old]['deps'] == ['linux-image-ia-armv8.0'], old
        assert devices[old]['env'] == {'KERNEL_SUFFIX': '-ia-armv8.0'}, old
    for recent in ('rpi5', 'rk3588'):
        assert devices[recent]['deps'] == ['linux-image-ia-armv8.2-lse'], recent
        assert devices[recent]['env'] == {
            'KERNEL_SUFFIX': '-ia-armv8.2-lse'
        }, recent
    # The kernel entries never name a device.
    kernel_entry = json.dumps(_packages()['linux-image-profile'])
    for device in (
        'rpi3', 'rpi4', 'rpi5', 'rk3588', 'rk3566', 'h616', 'imx8m', 'mt8183'
    ):
        assert device not in kernel_entry, device


def test_every_arm_family_has_a_variant_and_a_fragment() -> None:
    """Each device module variant carries its embeded <SoC>.cfg fragment.

    One fragment per SoC family, not per board: the rpi3 fragment covers
    BCM2710A1 (Pi Zero 2 W), rk3566 covers the RK356x, h616 covers the sun50i
    family. A variant without its overlay file would make the CI build fail the
    "overlay missing" check at first build. The fragments are engine data
    (DaemonCores-CI build-deb/kernel-shared/modules) — skipped when the sibling
    engine checkout is not present locally.
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
    """L1: one kernel per (profile, flavour); enforcement is not a variant."""
    variants = _variants('linux-image-profile')
    assert not any('-nosign' in k for k in variants)
    # The enforcement is decided at install (module.sig_enforce=1 karg), so the
    # kernel itself is built without MODULE_SIG_FORCE.
    assert (
        _packages()['linux-image-profile']['env']['KERNEL_SIGNING_ENFORCE'] ==
        'no'
    )
    assert all(
        'unsigned-kernel' not in (v.get('when') or {})
        for v in variants.values()
    )


def test_kernel_build_provides_the_signed_names() -> None:
    """The profile kernel Provides the names images and modules install by."""
    build = _packages()['linux-image-profile']['build']
    assert 'linux-image-minimal${KERNEL_SUFFIX:-}-${DEB_ARCH}' in build
    assert 'OTHER_PKG' not in build
    assert 'daemoncores-kernel-${KERNEL_PROFILE}-${KVER}' in build
    # The virtual release name is provided versioned: the module pairs
    # Depends on linux-image-<KVER> (= kernel version) on either profile.
    assert 'linux-image-%s (= %s)' in build


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
    assert all(
        'unsigned-kernel' not in str(v.get('when') or {})
        for v in _variants('linux-image-profile').values()
    )


def test_unsigned_kernel_provides_the_signed_name_for_the_modules() -> None:
    """The profile kernel Provides the names the modules install by."""
    build = _packages()['linux-image-profile']['build']
    assert 'linux-image-minimal${KERNEL_SUFFIX:-}-${DEB_ARCH}' in build
    assert 'daemoncores-kernel-${KERNEL_PROFILE}-${KVER}' in build
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
        for level in ('x64v1', 'x64v2', 'x64v3', 'x64v4'):
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


def test_gpu_module_sets_expand_to_the_full_flavour_matrix() -> None:
    """FUSION (owner 05/11 19:2x + 19:3x): one merged set per (set, flavour).

    gpu-ia and gpu-gaming are fused modules-only builds over the profile
    kernel (amdgpu per the DC pin, i915/xe — and the NVIDIA OPEN modules on
    amd64, inside the same deb; arm64 carries the in-tree sets with no
    NVIDIA at all). The -nvidia variants are the loader-policy debs on top
    of their sibling fused set, amd64 ONLY (no ARM NVIDIA, ever).
    """
    expanded = {p['name'] for p in _expand('amd64')}
    arm64 = {p['name'] for p in _expand_arm64()}
    flavours = ('x64v1', 'x64v2', 'x64v3', 'x64v4')
    arm_flavours = ('armv8.0', 'armv8.2-lse', 'armv9-sve2')
    for sett in ('ia', 'gaming'):
        for flavour in flavours + arm_flavours:
            # Y compris x64v4: the full flavour matrix, both arches.
            expected = expanded if flavour in flavours else arm64
            assert f'gpu-{sett}-{flavour}' in expected, (sett, flavour)
        for flavour in flavours:
            assert f'gpu-{sett}-nvidia-{flavour}' in expanded, (sett, flavour)
            assert f'gpu-{sett}-nvidia-{flavour}' not in arm64
    amd64 = _packages()
    set_entry = amd64['linux-modules-gpu']
    assert set_entry['variant-env'] == 'GPU_VARIANT'
    assert set_entry['sources'][1] == 'kernel-src/modules/gpu'
    assert set_entry['sources'][2] == 'nvidia'
    assert set_entry['deb-glob'] == 'gpu-{variant}_*'
    variants = amd64['linux-modules-gpu']['variants']
    for sett in ('ia', 'gaming'):
        for flavour in flavours + arm_flavours:
            assert variants[f'{sett}-{flavour}']['deps'] == [
                f'linux-image-ia-{flavour}'
            ], (sett, flavour)
            assert variants[f'{sett}-{flavour}']['env']['GPU_SET'] == sett
            assert variants[f'{sett}-{flavour}']['env']['GPU_FLAV'] == flavour
    for flavour in flavours:
        assert variants[f'ia-nvidia-{flavour}']['deps'] == [
            f'linux-image-ia-{flavour}',
            f'gpu-ia-{flavour}',
        ]
    for name in ('gpu-ia', 'gpu-gaming', 'gpu-ia-nvidia', 'gpu-gaming-nvidia'):
        assert name not in arm64


def _expand_arm64() -> list[dict[str, Any]]:
    """Expand the manifest for arm64 (the sibling helper is amd64-bound).

    Returns:
        The resolved package entry dicts.
    """
    return _expand('arm64')


def test_gpu_module_set_overlays_pin_their_profile() -> None:
    """Each set overlay pins its Display Core build; HSA stays compute on.

    gpu-ia: CONFIG_DRM_AMD_DC explicitly unset (the transverse kernel
    fragment default is overridden last-wins by the overlay), HSA/KFD on.
    gpu-gaming: DC on with fbcon. HDCP/DSC/FP are DEAD pins on the 7.2.15
    tree — amdgpu/Kconfig selects the DRM_DISPLAY_* helpers directly, and
    the FULL-SET rewrite dropped them (asserting them would re-introduce
    dead symbols the kconfig gate would reject).

    Returns:
        None. Asserts the set overlays pin their profile shape.
    """
    mod = (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'modules' /
        'gpu'
    )

    def _txt(sub: str) -> str:
        """The concatenated .cfg text of one GPU module-set directory.

        Args:
            sub: the set subdirectory ('ia' or 'gaming').

        Returns:
            The newline-joined text of every .cfg file, sorted by name.
        """
        return '\n'.join(
            p.read_text(encoding='utf-8')
            for p in sorted((mod / sub).glob('*.cfg'))
        )

    ia = _txt('ia')
    gaming = _txt('gaming')
    assert '# CONFIG_DRM_AMD_DC is not set' in ia
    assert 'CONFIG_HSA_AMD=y' in ia
    assert 'CONFIG_HSA_AMD_SVM=y' in ia
    for option in (
        'CONFIG_DRM_AMD_DC=y',
        'CONFIG_DRM_AMD_DC_SI=y',
        'CONFIG_FRAMEBUFFER_CONSOLE=y',
    ):
        assert option in gaming, option
    for dead in (
        'CONFIG_DRM_AMD_DC_FP=y',
        'CONFIG_DRM_AMD_DC_HDCP=y',
        'CONFIG_DRM_AMD_DC_DSC=y',
    ):
        assert dead not in gaming, dead
    assert 'CONFIG_DRM_AMD_DC=y' not in ia


def test_gpu_module_sets_ship_their_loader_policy() -> None:
    """Every set carries its /etc/modprobe.d policy file.

    The in-tree sets blacklist nothing of each other (exactly one is installed);
    the compute profiles keep nouveau away from the open NVIDIA modules, gaming
    pins dc=1 and the gaming-NVIDIA policy enables the nvidia_drm modeset.
    """
    conf_dir = (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'modprobe'
    )
    assert (conf_dir / 'dc-gpu-ia.conf'
            ).read_text().rstrip().endswith('blacklist nouveau')
    assert 'options amdgpu dc=1' in (conf_dir /
                                     'dc-gpu-gaming.conf').read_text()
    assert 'blacklist nouveau' in (conf_dir /
                                   'dc-gpu-ia-nvidia.conf').read_text()
    gaming_nv = (conf_dir / 'dc-gpu-gaming-nvidia.conf').read_text()
    assert 'blacklist nouveau' in gaming_nv
    assert 'options nvidia-drm modeset=1' in gaming_nv
    build = _packages()['linux-modules-gpu']['build']
    assert 'cp "${CONF_DIR}/dc-gpu-${GPU_SET}.conf"' in build.replace(
        "'\"", '"'
    )
    assert 'etc/modprobe.d' in build


def test_gpu_module_sets_own_the_kernel_paths_once() -> None:
    """The in-tree sets replace the kernel deb's =m gpu modules, exactly one.

    The control template carries the Replaces/Conflicts placeholders and the
    build computes both: Replaces pins the exact kernel deb, the two in-tree
    sets conflict with each other so exactly one profile build exists; the
    loader-policy variants ship no conflict (their sibling carries it).
    """
    control = (
        REPO / 'workflows' / 'bootc-debs-builder' / 'preinstall' / 'output' /
        'linux-modules-gpu' / 'DEBIAN' / 'control'
    ).read_text(encoding='utf-8')
    for field in (
        'Depends: {{ DEPS }}', 'Replaces: {{ REPLACES }}',
        'Conflicts: {{ CONFLICTS }}'
    ):
        assert field in control, field
    build = _packages()['linux-modules-gpu']['build']
    assert 'REPLACES="daemoncores-kernel-ia-${KVER} (= ${BUILT_VER})"' in build
    assert 'gpu-${OTHER}-${GPU_FLAVS}' in build
    # The profile build is proved in the build: DC pin greps the final config.
    assert 'CONFIG_DRM_AMD_DC is not set$' in build
    assert 'CONFIG_DRM_AMD_DC=y$' in build
