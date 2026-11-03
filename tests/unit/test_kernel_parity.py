"""Patch-parity pins of the shared kernel kconfig fragments.

PATCH PARITY (owner, 2026-11-03, re-arbitrated 12:55): the canonical shared
kernel build data (patches-shared.yml + kconfig fragments) lives in the build
engine — DaemonCores-CI build-deb/kernel-shared — and is exported to every build
as CI_KERNEL_SHARED. This repository carries NO copy of that data: the debian
linux-image build (packages.yml) consumes the export, and DaemonCores-VE kernel-
pve consumes the same export in its own engine checkout. These tests pin the
arbitrated functional set (owner 2026-11-03 12:14 revised) so a lane cannot
silently lose it, plus the consumer contract of THIS repository.
"""

import re
from pathlib import Path

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

    IO_URING=y, NTSYNC=m (Wine/Proton), the BORE knob and the XanMod timing host
    profile (HZ_1000 + full preemption) live in the shared file.
    """
    cfg = _cfg()
    for line in (
        'CONFIG_IO_URING=y',
        'CONFIG_NTSYNC=m',
        'CONFIG_SCHED_BORE=y',
        'CONFIG_HZ_1000=y',
        'CONFIG_PREEMPT=y',
        'CONFIG_PREEMPT_DYNAMIC=y',
    ):
        assert f'{line}\n' in cfg


def test_canonical_patch_set_shape() -> None:
    """One patch list, two consumers: 17 xanmod + 3 clearlinux + bore + the
    debian-lane module carrier (rocknix-btrtl, moved from packages.yml by
    the 13:05 arbitration).

    0004-ata-before-graphics and 0003-kbuild-sms-pipelining must stay out (they
    no longer apply to the tracked series trees).
    """
    text = CANONICAL_PATCHES.read_text(encoding='utf-8')
    names = re.findall(r'- name: ([^\s]+)', text)
    assert '0004-ata-before-graphics' not in names
    assert '0003-kbuild-sms-pipelining' not in names
    assert '0001-bore.patch' in text
    assert 'rocknix-btrtl-rtl8733bu' in names
    assert len(names) == 22


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


def test_ve_consumer_uses_the_engine_export() -> None:
    """VE kernel entry consumes the set FROM the engine export, by path.

    No raw distfetch of this repository: the former DC_DATA_REF /
    dc_data_fetch pattern (pinned commit + sha256 raw URLs against a sibling
    production repo) is retired in favour of CI_KERNEL_SHARED. The THP
    arbitration is revoked lane-side (owner 2026-11-03 13:05): THP=never
    travels with the image-lane -thpnever twins, never a lane kconfig pin.
    The sibling
    checkout absent locally skips the assertions that need it — CI owns the
    cross-repo gate.
    """
    if not VE_MANIFEST.is_file():
        return
    text = VE_MANIFEST.read_text(encoding='utf-8')
    assert 'DC_DATA_REF=' not in text
    assert 'dc_data_fetch' not in text
    assert '"${CI_KERNEL_SHARED}/patches-shared.yml"' in text
    assert '"${CI_KERNEL_SHARED}/kconfig-shared"' in text
    # THP lane-side arbitration revoked (owner 2026-11-03 13:05, supersedes
    # the 12:14/12:55 pins): the shared fragment's ALWAYS pin wins on the PVE
    # lane too (full-LXC prime); THP=never travels with the image-lane
    # -thpnever twins (karg transparent_hugepage=never), NEVER a lane-side
    # kconfig pin, and the lane tree carries NO config line (empty
    # sur-rides.cfg kept on purpose — documentation + precedent).
    thp = (
        VE_MANIFEST.parents[1] / 'bootc-debs-builder' / 'kernel-pve' /
        'kconfig' / 'sur-rides.cfg'
    )
    assert thp.is_file()
    lane_text = thp.read_text(encoding='utf-8')
    assert 'CONFIG_TRANSPARENT_HUGEPAGE=y\n' not in lane_text
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_ALWAYS=n\n' not in lane_text
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=n\n' not in lane_text
