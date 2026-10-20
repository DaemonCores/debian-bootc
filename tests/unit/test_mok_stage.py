"""Unit tests for the installer helper ``mok-stage``.

The script hard-codes ``/usr/share/debian-bootc`` and ``/sys/firmware/efi``.
Each test copies it, rewrites those paths into a temporary directory and puts
stub ``mokutil`` and ``openssl`` binaries first on ``PATH``; the stub
``mokutil`` records its arguments so the tests can assert on the single
``--import`` call.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'usr' /
    'libexec' / 'debian-bootc' / 'mok-stage'
)

MOKUTIL = """#!/bin/bash
echo "$*" >> "${STUB_LOG}"
if [[ "$1" == "--test-key" ]]; then
  [[ "$2" == *enrolled* ]] && exit 0
  exit 1
fi
exit 0
"""

OPENSSL = '#!/bin/bash\ncat >/dev/null\necho hashed\n'


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """Build a sandbox root with stubs and the rewritten script.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        The sandbox root.
    """
    share = tmp_path / 'usr' / 'share' / 'debian-bootc'
    (share / 'mok.d').mkdir(parents=True)
    (tmp_path / 'efi').mkdir()
    (share / 'sb_signing.crt').write_text('CERT\n')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    for name, body in (('mokutil', MOKUTIL), ('openssl', OPENSSL)):
        (bindir / name).write_text(body)
        (bindir / name).chmod(0o755)
    text = SCRIPT.read_text()
    text = text.replace('/usr/share/debian-bootc', str(share)
                        ).replace('/sys/firmware/efi', str(tmp_path / 'efi'))
    script = tmp_path / 'mok-stage'
    script.write_text(text)
    script.chmod(0o755)
    return tmp_path


def run(
    root: Path, password: str = 'longenough\n'
) -> subprocess.CompletedProcess:
    """Run the sandboxed script with the stubs first on PATH.

    Args:
        root: Sandbox root.
        password: Text fed on stdin.

    Returns:
        The completed process.
    """
    env = dict(
        os.environ,
        PATH=f'{root / "bin"}:{os.environ["PATH"]}',
        STUB_LOG=str(root / 'log')
    )
    return subprocess.run([str(root / 'mok-stage')],
                          input=password,
                          env=env,
                          capture_output=True,
                          text=True,
                          check=False)


def imports(root: Path) -> list[str]:
    """Return the recorded ``mokutil --import`` command lines.

    Args:
        root: Sandbox root.

    Returns:
        The argument lines that start with ``--import``.
    """
    log = root / 'log'
    if not log.exists():
        return []
    return [
        line for line in log.read_text().splitlines()
        if line.startswith('--import')
    ]


def test_all_certificates_in_one_import(sandbox: Path) -> None:
    """The Secure Boot cert and every mok.d cert share one import.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    mok = sandbox / 'usr' / 'share' / 'debian-bootc' / 'mok.d'
    (mok / 'fork-a.crt').write_text('A\n')
    (mok / 'fork-b.pem').write_text('B\n')
    result = run(sandbox)
    assert result.returncode == 0, result.stderr
    lines = imports(sandbox)
    assert len(lines) == 1
    for name in ('sb_signing.crt', 'fork-a.crt', 'fork-b.pem'):
        assert name in lines[0]


def test_private_key_is_refused(sandbox: Path) -> None:
    """A file holding a private key is never enrolled.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    mok = sandbox / 'usr' / 'share' / 'debian-bootc' / 'mok.d'
    (
        mok / 'leak.pem'
    ).write_text('-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n')
    result = run(sandbox)
    assert result.returncode == 0, result.stderr
    assert 'leak.pem' not in imports(sandbox)[0]
    assert 'private key' in result.stderr


def test_enrolled_certificates_are_skipped(sandbox: Path) -> None:
    """Already enrolled certificates are left out; none left means exit 2.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    share = sandbox / 'usr' / 'share' / 'debian-bootc'
    (share / 'sb_signing.crt').rename(share / 'enrolled-sb.crt')
    text = (sandbox / 'mok-stage'
            ).read_text().replace('sb_signing.crt', 'enrolled-sb.crt')
    (sandbox / 'mok-stage').write_text(text)
    result = run(sandbox)
    assert result.returncode == 2
    assert not imports(sandbox)


def test_short_password_fails(sandbox: Path) -> None:
    """A password under 8 characters is rejected before any import.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    result = run(sandbox, 'short\n')
    assert result.returncode == 1
    assert not imports(sandbox)
