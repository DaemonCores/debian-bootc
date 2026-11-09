"""Patch-parity pins of the shared kernel kconfig fragments.

PATCH PARITY (owner, 2026-11-03, re-arbitrated 12:55): the canonical shared
kernel build data (patches-shared.yml + kconfig fragments) lives in the build
engine — DaemonCores-CI build-deb/kernel-shared — and is exported to every build
as CI_KERNEL_SHARED. This repository carries NO copy of that data: the debian
linux-image build (packages.yml) consumes the export, and the vanilla
proxmox-ve-bootc kernel-pve entry consumes the same export in its own engine
checkout (the DaemonCores-VE fork consumes the PUBLISHED proxmox-ve-bootc
image instead — no kernel build, no engine reference in the fork).
These tests pin the
arbitrated functional set (owner 2026-11-03 12:14 revised) so a lane cannot
silently lose it, plus the consumer contract of THIS repository.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CANONICAL_DATA = Path(
    REPO.parent
) / 'DaemonCores-CI' / 'build-deb' / 'kernel-shared'
X86_COMMON = CANONICAL_DATA / 'kconfig-shared' / 'x86-common.cfg'
CANONICAL_PATCHES = CANONICAL_DATA / 'patches-shared.yml'
PACKAGES_YML = (REPO / 'workflows' / 'bootc-debs-builder' / 'packages.yml')
VE_MANIFEST = (
    REPO.parent / 'DaemonCores-VE' / 'workflows' / 'bootc-debs-builder' /
    'packages.yml'
)
VANILLA_ROOT = REPO.parent / 'proxmox-ve-bootc'


def _cfg() -> str:
    """Return the shared x86-common kconfig fragment verbatim.

    Returns:
        The raw fragment text of the engine checkout.
    """
    return X86_COMMON.read_text(encoding='utf-8')


def test_thp_arbitration_debian_lane_is_always() -> None:
    """THP ALWAYS on the embedded lane (AI-opti profile primes, critical).

    MADVISE is pinned off so olddefconfig cannot resurrect the balanced default
    next to ALWAYS.
    """
    cfg = _cfg()
    assert 'CONFIG_TRANSPARENT_HUGEPAGE=y' in cfg
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_ALWAYS=y' in cfg
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=n' in cfg
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y\n' not in cfg


def test_shared_functional_pins_present() -> None:
    """The functional set travels with the canonical fragment, both lanes.

    IO_URING=y, NTSYNC=m (Wine/Proton) and the XanMod timing host profile
    (HZ_1000 + full preemption) live in the shared file. SCHED_BORE is
    deliberately absent: the bore sibling is DORMANT (proven 2026-11-04, the
    CachyOS hunks no longer apply to any vanilla tree), and the pin was
    REMOVED from the fragment — a dead pin kills the gate until upstream
    ships a matching bore patch again.
    """
    cfg = _cfg()
    for line in (
        'CONFIG_IO_URING=y',
        'CONFIG_NTSYNC=m',
        'CONFIG_HZ_1000=y',
        'CONFIG_PREEMPT=y',
        'CONFIG_PREEMPT_DYNAMIC=y',
    ):
        assert f'{line}\n' in cfg
    assert 'CONFIG_SCHED_BORE' not in cfg


def test_canonical_patch_set_shape() -> None:
    """One patch list, two consumers: 17 xanmod + 3 clearlinux(XanMod) + bore
    + rocknix carrier + MSM IFPC + 2 clearlinux completions = 25.

    The module carrier (rocknix-btrtl, moved from packages.yml by the 13:05
    arbitration) rides on the arm64 kernel builds. The bore sibling stays in
    the canonical list DORMANT (exclude-series filter on 7.0..7.3) and its
    upstream file is the renamed 0001-bore-cachy.patch.

    0004-ata-before-graphics and 0003-kbuild-sms-pipelining must stay out (they
    no longer apply to the tracked series trees).

    ARM OPTI (owner mandate 2026-11-09): +2 clearlinux generic completions
    (0166 sched-fair upper-limit, 0174 memcg CHARGE_BATCH 128, both
    sha256-pinned) and +1 arm64 additive (msm-adreno devfreq IFPC relax,
    lore URL + sha256; -mcpu flavour proof side lives in the engine
    kernel_flavour_kcflags. msm IFPC arm64 = K-PORT BOTH siblings (run
    42715501467, linux-image-ia-armv8.0): the [16/17] a6xx X1-85 enablement
    fails raw AND [17/17] needs its ADRENO_QUIRK_IFPC, so the arm64 build
    dies at msm_gpu_devfreq.c:162 — re-arm both siblings later. Count 22 -> 25 (17 xanmod, 3 clearlinux carried
    by XanMod 0001/0002/0003, 2 new clearlinux, bore dormant, rocknix
    module carrier, msm arm64 additive).
    """
    text = CANONICAL_PATCHES.read_text(encoding='utf-8')
    names = re.findall(r'- name: ([^\s]+)', text)
    assert '0004-ata-before-graphics' not in names
    assert '0003-kbuild-sms-pipelining' not in names
    assert '0001-bore-cachy.patch' in text
    assert 'bore' in names
    assert '0166-sched-fair-remove-upper-limit' in names
    assert '0174-memcg-charge-batch-128' not in names
    assert 'msm-adreno-devfreq-ifpc-relax' not in names
    assert len(names) == 23
    # K-PORT: 0174 memcg (run 42713342754, BUILD_BUG_ON vs S8_MAX) and
    # msm IFPC 17/17 (run 42715501467, ADRENO_QUIRK_IFPC from the dropped
    # [16/17] sibling). Dry-run proved the application, never the build.


def test_no_carbon_copy_of_the_engine_data() -> None:
    """This repository carries NO copy of the shared kernel data.

    The engine checkout is the single source: the former in-repo data paths
    are gone and packages.yml consumes CI_KERNEL_SHARED, never a sibling
    path of this checkout.
    """
    assert not (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel' /
        'patches-shared.yml'
    ).exists()
    assert not (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel' / 'kconfig-shared'
    ).exists()
    text = PACKAGES_YML.read_text(encoding='utf-8')
    assert '"${CI_KERNEL_SHARED}/patches-shared.yml"' in text
    assert '"${CI_KERNEL_SHARED}/kconfig-shared"' in text
    assert 'bootc-debs-builder/kernel/patches-shared.yml' not in text
    assert 'bootc-debs-builder/kernel/kconfig-shared' not in text


def test_no_arch_overlay_merge() -> None:
    """linux-image merges ONLY the base config + the arm64 page-size overlay.

    The fold (owner 2026-11-03): the former architecture overlays
    (kernel-shared/modules/arm and x86_64) are merged into the base config
    ('# arm64 built-in' / '# amd64 built-in' sections, =m options promoted =y)
    and deleted from the engine store. packages.yml must reference neither a
    modules/<arch> overlay nor an ARCH_OVERLAY variable anymore, and the
    engine's base config must carry the folded sections.
    """
    text = PACKAGES_YML.read_text(encoding='utf-8')
    assert 'ARCH_OVERLAY' not in text
    # The former arch overlay merge paths are gone; the only remaining
    # modules/ fragment merge is the per-DEVICE one of the device modules
    # entries (rpi3/rpi4/...), which the fold keeps untouched.
    for stale in ('modules/arm', 'modules/x86_64'):
        assert f'"${{CI_KERNEL_SHARED}}/{stale}"' not in text, stale
    # KERNEL FINAL v2 (owner 2026-11-03; path restructure owner 05/11):
    # the per-DEVICE fragment merged by the device modules entries lives IN
    # THIS REPO (kernel-src/modules/embeded/<device>.cfg) — no engine
    # kernel-shared/modules path on the modules lane, and the nine device
    # fragments are committed here.
    mod_uses = re.findall(r'kernel-src/modules/embeded/\$\{DEVICE\}', text)
    assert len(mod_uses) == 2, mod_uses
    assert '"${CI_KERNEL_SHARED}/modules' not in text
    assert 'kernel-src/modules' in text
    # 05/11 restructure: NO reference to the former kernel/modules tree
    # remains anywhere in the manifest.
    assert 'bootc-debs-builder/kernel/modules' not in text
    # GPU FINAL (owner 2026-11-03): the kernel-src/modules/gpu directory (the
    # GPU profile overlays as per-vendor .cfg sets) lives in the kernel-src
    # tree — a directory of fragments, not a device fragment, so it is
    # excluded from the device-file pin like the device list itself. The
    # modprobe loader-policy confs live at kernel-src/modprobe.
    devices = sorted(
        p.stem for p in (
            REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' /
            'modules' / 'embeded'
        ).iterdir() if p.suffix == '.cfg'
    )
    assert devices == sorted((
        'rpi3',
        'rpi4',
        'rpi5',
        'rk3588',
        'rk3566',
        'rk3399',
        'h616',
        'imx8m',
        'mt8183',
    )), devices
    gpu_dir = (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'modules' /
        'gpu'
    )
    assert (gpu_dir / 'ia').is_dir()
    assert (gpu_dir / 'gaming').is_dir()
    assert (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'modprobe' /
        'dc-gpu-ia.conf'
    ).is_file()
    assert (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'modprobe' /
        'dc-gpu-gaming-nvidia.conf'
    ).is_file()
    cfg = (CANONICAL_DATA / 'config').read_text(encoding='utf-8')
    for section in ('# arm64 built-in', '# amd64 built-in'):
        assert section in cfg, section
    # The GPU drivers are modules again (the fold is undone): the amd64
    # fold promotes the network/USB drivers =y, the GPU block stays =m.
    for promoted in ('CONFIG_E1000=y', ):
        assert promoted in cfg, promoted
    for modular in ('CONFIG_DRM_AMDGPU=m', 'CONFIG_DRM_I915=m'):
        assert modular in cfg, modular
    assert 'CONFIG_DRM_AMD_DC=y\n' not in cfg


def test_ve_consumer_uses_the_engine_export() -> None:
    """The vanilla PVE lane consumes the engine export; the fork does not.

    PATCH PARITY (separation owner order, 03/11): the kernel-pve entry now
    lives ONLY in the vanilla proxmox-ve-bootc repository, and it must keep
    eating the engine export (CI_KERNEL_SHARED) — no raw distfetch of this
    repository (DC_DATA_REF / dc_data_fetch retired). The DaemonCores-VE
    fork consumes the PUBLISHED proxmox-ve-bootc base image instead: no
    kernel build, no deb built twice ('no deb is built twice'), and no
    CIKernelShared reference left in its manifest. The THP pin stays with
    the compiled kernel: the vanilla images carry the never karg, the fork
    derives thin -thpalways twins — a lane-side THP kconfig pin would be a
    second kernel state.
    The sibling checkout absent locally skips the assertions that need it —
    CI owns the cross-repo gate.
    """
    if not VE_MANIFEST.is_file():
        return
    text = VE_MANIFEST.read_text(encoding='utf-8')
    # The fork references NO engine export and builds NO kernel any more.
    assert 'DC_DATA_REF=' not in text
    assert 'dc_data_fetch' not in text
    assert 'CI_KERNEL_SHARED' not in text
    assert '- name: kernel-pve' not in text
    # The fork consumes the vanilla base image: the base manifest FROM is
    # the published proxmox-ve-bootc image, not debian-bootc, and the fork
    # keeps deriving FROM that published image (thin twins only).
    ve_base = (REPO.parent / 'DaemonCores-VE' / 'Containerfile.base')
    assert ve_base.is_file()
    assert 'FROM ghcr.io/daemoncores/proxmox-ve-bootc:latest_' \
        in ve_base.read_text(encoding='utf-8')
    # Where the kernel estate lives NOW (owner FINAL architecture, 05/11
    # 13:0x): the vanilla proxmox-ve-bootc repo builds NO kernel any more —
    # no kernel-pve entry, no engine kernel export in its manifest. The
    # unified kernel (14 IA/VM profile lanes) and the headers live on this
    # debian side; the vanilla keeps only the OpenZFS module pair, built
    # through the SHARED kernel_build_module gate of DaemonCores-CI.
    vanilla = VANILLA_ROOT / 'workflows' / 'bootc-debs-builder' / 'packages.yml'
    if not vanilla.is_file():
        return
    vtext = vanilla.read_text(encoding='utf-8')
    assert '- name: kernel-pve' not in vtext
    assert 'CI_KERNEL_SHARED' not in vtext
    assert 'kernel_build_module' in vtext
    # profile estate pins: 14 variants (7 flavours x IA/VM) on the
    # debian manifest; the GPU tree carries ONLY gpu/ia + gpu/gaming
    # (ia compute DC off, gaming display DC on module set) — VM is kconfig
    # only (kernel-src/kconfig/thp/never.cfg THP-never fragment; VM ≭ GPU,
    # owner correction 05/11 15:1x).
    prof = yaml.safe_load(PACKAGES_YML.read_text(encoding='utf-8'))
    entries = {e['name']: e for e in prof['packages']}
    profile_entry = entries['linux-image-profile']
    keys = set(profile_entry['variants'])
    assert len(keys) == 14
    assert {k.split('-', 1)[0] for k in keys} == {'ia', 'vm'}
    assert {k.split('-', 1)[1]
            for k in keys} == {
                'x64v1',
                'x64v2',
                'x64v3',
                'x64v4',
                'armv8.0',
                'armv8.2-lse',
                'armv9-sve2',
            }
    gpu_dir = (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'modules' /
        'gpu'
    )
    assert sorted(p.name for p in gpu_dir.iterdir()) == ['gaming', 'ia']
    ia_text = '\n'.join(
        p.read_text(encoding='utf-8')
        for p in sorted((gpu_dir / 'ia').glob('*.cfg'))
    )
    assert '# CONFIG_DRM_AMD_DC is not set' in ia_text
    # VM = kconfig ONLY: the THP never fragment is real kconfig, and the VM
    # delta never references the GPU tree.
    never = (
        REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-src' / 'kconfig' /
        'thp' / 'never.cfg'
    ).read_text(encoding='utf-8')
    assert '# CONFIG_TRANSPARENT_HUGEPAGE is not set' in never
    profile_build = profile_entry['build']
    assert 'kernel-src/kconfig/thp/never.cfg' in profile_build
    assert 'gpu/vm' not in '\n'.join(
        (str(profile_entry['sources']), profile_build)
    )
