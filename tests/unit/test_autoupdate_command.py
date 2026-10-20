"""Unit tests for the ``autoupdate`` command.

The script works under ``$INSTALL_ROOT`` so it can run outside an image.
"""

import os
import subprocess
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / 'src'
SCRIPT = SRC / 'debianpostinstall' / 'usr' / 'bin' / 'autoupdate'
MASK = 'etc/systemd/system/bootc-fetch-apply-updates.timer'


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``autoupdate`` against a scratch root.

    Args:
        root: Directory used as ``INSTALL_ROOT``.
        *args: Command-line arguments.

    Returns:
        The completed process, with captured text output.
    """
    return subprocess.run([str(SCRIPT), *args],
                          check=False,
                          capture_output=True,
                          text=True,
                          env={
                              **os.environ, 'INSTALL_ROOT': str(root)
                          },
                          timeout=10)


def test_disable_masks_the_timer(tmp_path: Path) -> None:
    """Disabling links the timer to /dev/null and status reports it.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    assert _run(tmp_path, 'disable').returncode == 0
    assert os.readlink(tmp_path / MASK) == '/dev/null'
    assert 'disabled' in _run(tmp_path, 'status').stdout


def test_enable_removes_the_mask(tmp_path: Path) -> None:
    """Enabling removes the mask; repeating either action is harmless.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    _run(tmp_path, 'disable')
    assert _run(tmp_path, 'disable').returncode == 0
    assert _run(tmp_path, 'enable').returncode == 0
    assert not (tmp_path / MASK).is_symlink()
    assert _run(tmp_path, 'enable').returncode == 0
    assert 'enabled' in _run(tmp_path, 'status').stdout


def test_enable_keeps_a_real_unit_file(tmp_path: Path) -> None:
    """A unit file that is not the mask is never deleted.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    unit = tmp_path / MASK
    unit.parent.mkdir(parents=True)
    unit.write_text('[Timer]\n')
    result = _run(tmp_path, 'enable')
    assert result.returncode == 1
    assert unit.read_text() == '[Timer]\n'


def test_bad_usage_is_rejected(tmp_path: Path) -> None:
    """Missing or unknown arguments exit with status 2.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    assert _run(tmp_path).returncode == 2
    assert _run(tmp_path, 'bogus').returncode == 2


def test_both_images_ship_the_same_scripts() -> None:
    """The standard and the minimal image carry identical shared scripts."""
    libexec = Path('usr/libexec/debian-bootc')
    for name in (
        Path('usr/bin/autoupdate'), libexec / 'ostree-layout',
        libexec / 'install-signature-policy'
    ):
        assert (SRC / 'debianpostinstall' /
                name).read_bytes() == (SRC / 'minimalpostinstall' /
                                       name).read_bytes()
