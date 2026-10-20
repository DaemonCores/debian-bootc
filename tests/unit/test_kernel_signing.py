"""Unit tests for ``lib/kernel-signing.sh`` against a fake kernel tree.

``scripts/config`` is replaced by a stub that records its arguments, so the
tests prove what the library forces when signing is active and that it forces
nothing when it is not.
"""

import os
import subprocess
from pathlib import Path

import pytest

LIB = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'lib' / 'kernel-signing.sh'
)

CONFIG_STUB = '#!/bin/bash\necho "$*" >> "${STUB_LOG}"\n'


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Build a fake kernel source tree.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        The tree root.
    """
    (tmp_path / 'scripts').mkdir()
    stub = tmp_path / 'scripts' / 'config'
    stub.write_text(CONFIG_STUB)
    stub.chmod(0o755)
    return tmp_path


def call(tree: Path, function: str, **env: str) -> subprocess.CompletedProcess:
    """Run one library function from the fake tree.

    Args:
        tree: Fake kernel tree, used as the working directory.
        function: Library function to call.
        **env: Extra environment variables.

    Returns:
        The completed process.
    """
    full_env = dict(os.environ, STUB_LOG=str(tree / 'log'), **env)
    return subprocess.run(
        ['bash', '-c', f'. {LIB}; {function}'],
        cwd=tree,
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )


def logged(tree: Path) -> str:
    """Return what the ``scripts/config`` stub recorded.

    Args:
        tree: Fake kernel tree.

    Returns:
        The recorded arguments, empty when nothing was called.
    """
    log = tree / 'log'
    return log.read_text() if log.exists() else ''


def test_active_forces_enforcement_and_keyrings(tree: Path) -> None:
    """Active signing writes the key and forces the enforcement options.

    Args:
        tree: Fake kernel tree.
    """
    result = call(
        tree,
        'kernel_signing_setup',
        MODULE_SIGNING_ACTIVE='yes',
        MODULE_SIGNING_KEY='KEY',
        MODULE_SIGNING_CERT='CERT'
    )
    assert result.returncode == 0, result.stderr
    assert (tree / 'certs' / 'signing_key.x509').read_text() == 'CERT\n'
    for option in (
        'MODULE_SIG_FORCE', 'INTEGRITY_MACHINE_KEYRING',
        'SECONDARY_TRUSTED_KEYRING'
    ):
        assert f'--enable {option}' in logged(tree)


def test_inactive_forces_nothing(tree: Path) -> None:
    """Without the option nothing is forced and no key is written.

    Args:
        tree: Fake kernel tree.
    """
    result = call(tree, 'kernel_signing_setup', MODULE_SIGNING_ACTIVE='no')
    assert result.returncode == 0, result.stderr
    assert 'FORCE' not in logged(tree)
    assert '--enable' not in logged(tree)
    assert not (tree / 'certs').exists()


def test_active_without_key_fails(tree: Path) -> None:
    """Active signing without a key stops the build.

    Args:
        tree: Fake kernel tree.
    """
    result = call(tree, 'kernel_signing_setup', MODULE_SIGNING_ACTIVE='yes')
    assert result.returncode == 1


def test_verify_detects_a_dropped_option(tree: Path) -> None:
    """A forced option missing from .config fails the build when active.

    Args:
        tree: Fake kernel tree.
    """
    (tree / '.config').write_text('CONFIG_MODULE_SIG=y\n')
    failed = call(tree, 'kernel_signing_verify', MODULE_SIGNING_ACTIVE='yes')
    assert failed.returncode == 1
    assert 'CONFIG_MODULE_SIG_FORCE' in failed.stderr
    skipped = call(tree, 'kernel_signing_verify', MODULE_SIGNING_ACTIVE='no')
    assert skipped.returncode == 0
