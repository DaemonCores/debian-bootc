"""Unit tests for the ``kernel_apply_patches`` CI helper.

Upstream is replaced by ``file://`` URLs, so no network is needed. The
primitives live in DaemonCores-CI ``scripts/kernel_helpers.sh`` (the
standard kernel helper, commit fb5b1a8); the debian-bootc manifests stay
the declarative patches.yml consumed through ``kernel_patch_list``.
"""

import subprocess
from pathlib import Path

import pytest

LIB = (
    Path(__file__).resolve().parents[3] / 'DaemonCores-CI' / 'scripts' /
    'kernel_helpers.sh'
)
pytestmark = pytest.mark.skipif(
    not LIB.is_file(), reason='DaemonCores-CI scripts not available'
)
PATCH_ONE = """--- a/file
+++ b/file
@@ -1 +1 @@
-base
+one
"""
PATCH_TWO = """--- a/file
+++ b/file
@@ -1 +1 @@
-one
+two
"""
PATCH_BAD = """--- a/file
+++ b/file
@@ -1 +1 @@
-nothing like it
+x
"""


@pytest.fixture(name='setup')
def fixture_setup(tmp_path: Path) -> Path:
    """Build a source tree and the upstream patch files.

    Args:
        tmp_path: Pytest scratch directory.

    Returns:
        The scratch directory holding ``tree/`` and the patch files.
    """
    (tmp_path / 'tree').mkdir()
    (tmp_path / 'tree' / 'file').write_text('base\n')
    for name, body in (('one', PATCH_ONE), ('two', PATCH_TWO),
                       ('bad', PATCH_BAD)):
        (tmp_path / f'{name}.patch').write_text(body)
    return tmp_path


def _manifest(root: Path, entries: list[tuple[str, str, str, str]]) -> Path:
    """Write a patch manifest.

    Args:
        root: Scratch directory, also the upstream root.
        entries: ``(name, patch file, stage, class)`` per patch.

    Returns:
        The manifest path.
    """
    lines = ['patches:']
    for name, file, stage, klass in entries:
        lines += [
            f'  - name: {name}', f'    url: file://{root}/{file}',
            f'    stage: {stage}', f'    class: {klass}'
        ]
    path = root / 'patches.yml'
    path.write_text('\n'.join(lines) + '\n')
    return path


def _apply(root: Path,
           manifest: Path,
           arch: str = 'amd64') -> subprocess.CompletedProcess[str]:
    """Run ``kernel_apply_patches`` for the kernel class.

    Args:
        root: Scratch directory holding ``tree/``.
        manifest: Patch manifest.
        arch: Architecture to apply.

    Returns:
        The completed process.
    """
    script = (
        f'set -euo pipefail; . {LIB}; '
        f'kernel_apply_patches {manifest} {arch} 7.2.11 {root}/tree kernel'
    )
    return subprocess.run(['bash', '-c', script],
                          check=False,
                          capture_output=True,
                          text=True,
                          timeout=60)


def test_common_then_architecture_in_order(setup: Path) -> None:
    """Common patches go first, then the architecture ones.

    Args:
        setup: Source tree and patch files.
    """
    manifest = _manifest(
        setup, [('first', 'one.patch', 'common', 'kernel'),
                ('second', 'indep.patch', 'amd64', 'kernel')]
    )
    # The second patch is independent (another file), so the whole-set
    # dry-run sees a pristine, coherent tree; the applied order is
    # stage-staged (common first), whatever the manifest order is.
    (setup / 'tree' / 'file2').write_text('upstream other\n')
    patch_body = (
        '--- a/file2\n'
        '+++ b/file2\n'
        '@@ -1 +1 @@\n'
        '-upstream other\n'
        '+patched other\n'
    )
    (setup / 'indep.patch').write_text(patch_body)
    result = _apply(setup, manifest)
    assert result.returncode == 0, result.stderr
    out = result.stdout.splitlines()
    assert out.index('applied patch first') < out.index('applied patch second')


def test_other_architecture_and_module_class_are_skipped(setup: Path) -> None:
    """A patch of another architecture or of the module class is not applied.

    Args:
        setup: Source tree and patch files.
    """
    manifest = _manifest(
        setup, [('arm', 'one.patch', 'arm64', 'kernel'),
                ('mod', 'one.patch', 'common', 'module')]
    )
    assert _apply(setup, manifest).returncode == 0
    assert (setup / 'tree' / 'file').read_text() == 'base\n'


def test_patch_that_does_not_apply_fails_hard(setup: Path) -> None:
    """A patch that does not apply fails and names itself.

    Args:
        setup: Source tree and patch files.
    """
    manifest = _manifest(setup, [('broken', 'bad.patch', 'common', 'kernel')])
    result = _apply(setup, manifest)
    assert result.returncode == 1
    assert 'patch broken does not apply' in result.stderr


def test_missing_patch_fails_hard(setup: Path) -> None:
    """A patch that cannot be downloaded fails the build.

    Args:
        setup: Source tree and patch files.
    """
    manifest = _manifest(setup, [('gone', 'absent.patch', 'common', 'kernel')])
    result = _apply(setup, manifest)
    assert result.returncode == 1
    assert 'cannot download patch gone' in result.stderr


def test_moved_context_is_refused_not_fuzzed(setup: Path) -> None:
    """A hunk whose context changed upstream is refused, never fuzzed in.

    The default ``patch`` fuzz of 2 would apply this hunk although two of its
    context lines no longer match; the strict dry-run (--fuzz=0) refuses it
    and leaves the tree untouched.

    Args:
        setup: Source tree and patch files.
    """
    (setup / 'tree' / 'file').write_text('c1\nc2\nc3\nold\nd1\nd2\nd3\n')
    (setup / 'fuzzy.patch').write_text(
        '--- a/file\n+++ b/file\n@@ -1,7 +1,7 @@\n'
        ' c1\n X2\n c3\n-old\n+new\n d1\n d2\n d3\n'
    )
    manifest = _manifest(setup, [('fuzzy', 'fuzzy.patch', 'common', 'kernel')])
    result = _apply(setup, manifest)
    assert result.returncode == 1
    assert 'patch fuzzy does not apply' in result.stderr
    assert (setup / 'tree' /
            'file').read_text() == 'c1\nc2\nc3\nold\nd1\nd2\nd3\n'


def test_entry_fuzz_allows_a_moved_context_for_that_patch_only(
    setup: Path
) -> None:
    """A manifest entry with ``fuzz: 2`` applies the moved-context hunk.

    Args:
        setup: Source tree and patch files.
    """
    (setup / 'tree' / 'file').write_text('c1\nc2\nc3\nold\nd1\nd2\nd3\n')
    (setup / 'fuzzy.patch').write_text(
        '--- a/file\n+++ b/file\n@@ -1,7 +1,7 @@\n'
        ' c1\n X2\n c3\n-old\n+new\n d1\n d2\n d3\n'
    )
    manifest = _manifest(setup, [('fuzzy', 'fuzzy.patch', 'common', 'kernel')])
    manifest.write_text(manifest.read_text() + '    fuzz: 2\n')
    result = _apply(setup, manifest)
    assert result.returncode == 0, result.stderr
    assert (setup / 'tree' / 'file').read_text().splitlines()[3] == 'new'


def test_fuzz_override_reports_drift_as_a_warning(setup: Path) -> None:
    """A fuzz override that places a hunk by fuzz is reported, never silent.

    Args:
        setup: Source tree and patch files.
    """
    (setup / 'tree' / 'file').write_text('c1\nc2\nc3\nold\nd1\nd2\nd3\n')
    (setup / 'fuzzy.patch').write_text(
        '--- a/file\n+++ b/file\n@@ -1,7 +1,7 @@\n'
        ' c1\n X2\n c3\n-old\n+new\n d1\n d2\n d3\n'
    )
    manifest = _manifest(setup, [('fuzzy', 'fuzzy.patch', 'common', 'kernel')])
    manifest.write_text(manifest.read_text() + '    fuzz: 2\n')
    result = _apply(setup, manifest)
    assert result.returncode == 0, result.stderr
    assert '::warning::patch fuzzy applies' in result.stdout
    assert 'only with fuzz 2' in result.stdout


def test_unneeded_fuzz_override_is_reported(setup: Path) -> None:
    """A fuzz override on a patch that applies strictly is flagged.

    Args:
        setup: Source tree and patch files.
    """
    (setup / 'tree' / 'file').write_text('c1\nold\nd1\n')
    (setup / 'clean.patch').write_text(
        '--- a/file\n+++ b/file\n@@ -1,3 +1,3 @@\n c1\n-old\n+new\n d1\n'
    )
    manifest = _manifest(setup, [('clean', 'clean.patch', 'common', 'kernel')])
    manifest.write_text(manifest.read_text() + '    fuzz: 2\n')
    result = _apply(setup, manifest)
    assert result.returncode == 0, result.stderr
    assert 'fuzz 2 is no longer needed' in result.stdout
