"""Static checks of ``workflows/tests.yml``, mirroring the CI harness.

The harness (``DaemonCores-CI/image-test/image-test.sh``) refuses to boot the
VM when a test lacks ``name``, ``run`` or ``diag``.  These tests surface the
same manifest errors locally in well under a second instead of after a build.
"""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

MANIFEST = Path(__file__).resolve().parents[2] / 'workflows' / 'tests.yml'
SECTIONS = ('tests', 'reboot_tests')
ARCHES = {'amd64', 'arm64'}
VARIANTS = {'main', 'minimal'}


def _load() -> dict[str, Any]:
    """Parse ``workflows/tests.yml``.

    Returns:
        The manifest as a mapping.
    """
    return cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))


def _entries() -> list[tuple[str, int, dict[str, Any]]]:
    """List every test entry of every section of the manifest.

    Returns:
        One ``(section, index, entry)`` tuple per entry.
    """
    data = _load()
    return [(section, i, cast(dict[str, Any], entry)) for section in SECTIONS
            for i, entry in enumerate(data.get(section) or [])]


def test_manifest_has_tests_and_timeouts() -> None:
    """The manifest declares tests and positive integer timeouts."""
    data = _load()
    assert data['tests']
    assert isinstance(data['boot_timeout'], int)
    assert data['boot_timeout'] > 0
    assert isinstance(data['reboot_timeout'], int)
    assert data['reboot_timeout'] > 0


@pytest.mark.parametrize(('section', 'index', 'entry'), _entries())
def test_entry_has_name_run_diag(
    section: str, index: int, entry: dict[str, Any]
) -> None:
    """Every entry ships name, run and diag, as the harness requires.

    Args:
        section: Manifest section the entry belongs to.
        index: Position of the entry inside its section.
        entry: The test entry itself.
    """
    where = f'{section}[{index}]'
    for key in ('name', 'run', 'diag'):
        value = entry.get(key)
        assert isinstance(value, str), f'{where} lacks {key}'
        assert value.strip(), f'{where} lacks {key}'


@pytest.mark.parametrize(('section', 'index', 'entry'), _entries())
def test_entry_gates_are_known(
    section: str, index: int, entry: dict[str, Any]
) -> None:
    """``arch`` and ``variant`` gates only use values the harness knows.

    Args:
        section: Manifest section the entry belongs to.
        index: Position of the entry inside its section.
        entry: The test entry itself.
    """
    where = f'{section}[{index}]'
    assert entry.get('arch', 'amd64') in ARCHES, f'{where} bad arch'
    assert entry.get('variant', 'main') in VARIANTS, f'{where} bad variant'


def test_test_names_are_unique_per_section() -> None:
    """Duplicate names would make CI logs ambiguous."""
    for section in SECTIONS:
        names = [e['name'] for e in _load().get(section) or []]
        assert len(names) == len(set(names)), f'duplicate name in {section}'
