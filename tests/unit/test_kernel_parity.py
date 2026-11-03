"""Patch-parity pins of the shared kernel-pve kconfig fragment.

PATCH PARITY (owner, 2026-11-03): the kernel-pve kconfig fragments in this
repository are THE canonical data both kernels consume — the debian
linux-image build merges them in-repo (packages.yml) and DaemonCores-VE
consumes them by pinned commit + sha256. These tests pin the arbitrated
functional set (owner 2026-11-03 12:14 revised) so a lane cannot silently
lose it, and the reference-mode contract of the VE consumer (never a copy).
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
X86_COMMON = (
    REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-pve' / 'kconfig' /
    'x86-common.cfg'
)
CANONICAL_PATCHES = (
    REPO / 'workflows' / 'bootc-debs-builder' / 'kernel-pve' / 'patches.yml'
)
VE_MANIFEST = (
    REPO.parent / 'DaemonCores-VE' / 'workflows' / 'bootc-debs-builder' /
    'packages.yml'
)


def _cfg() -> str:
    """Return the shared x86-common kconfig fragment verbatim.

    Returns:
        The raw fragment text.
    """
    return X86_COMMON.read_text(encoding='utf-8')


def test_thp_arbitration_debian_lane_is_always() -> None:
    """THP ALWAYS on the embedded lane (AI-opti profile primes, critical).

    MADVISE is pinned off so olddefconfig cannot resurrect the balanced
    default next to ALWAYS.
    """
    cfg = _cfg()
    assert 'CONFIG_TRANSPARENT_HUGEPAGE=y' in cfg
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_ALWAYS=y' in cfg
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=n' in cfg
    assert 'CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y\n' not in cfg


def test_shared_functional_pins_present() -> None:
    """The functional set travels with the canonical fragment, both lanes.

    IO_URING=y, NTSYNC=m (Wine/Proton), the BORE knob and the XanMod timing
    host profile (HZ_1000 + full preemption) live in the shared file.
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
    """One patch list, two consumers: 17 xanmod + 3 clearlinux + bore.

    0004-ata-before-graphics and 0003-kbuild-sms-pipelining must stay out
    (they no longer apply to the tracked series trees).
    """
    text = CANONICAL_PATCHES.read_text(encoding='utf-8')
    names = re.findall(r'- name: ([^\s]+)', text)
    assert '0004-ata-before-graphics' not in names
    assert '0003-kbuild-sms-pipelining' not in names
    assert '0001-bore.patch' in text
    assert len(names) == 21


def test_ve_consumer_is_reference_mode() -> None:
    """VE kernel-pve consumes the set BY REFERENCE, pinned commit + sha256.

    The VE entry defines no native patch data, and the local kconfig copy
    is deleted; its lane-local THP pin is NEVER (hugepages belong to the
    PVE guests). The sibling checkout absent locally skips the assertions
    that need it — CI owns the cross-repo gate.
    """
    if not VE_MANIFEST.is_file():
        return
    text = VE_MANIFEST.read_text(encoding='utf-8')
    assert 'DC_DATA_REF=' in text
    assert 'kernel-pve/patches.yml' in text
    assert 'kernel_apply_patches "${PATCHES_FILE}"' in text
    assert 'DC_DATA_BASE=' in text
    assert 'TRANSPARENT_HUGEPAGE_ALWAYS=n' in text
    assert not (VE_MANIFEST.parent / 'kernel-pve' / 'kconfig').exists()
