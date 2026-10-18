"""Unit tests for ``scripts/rotate-apt-key.sh``.

A stub ``gh`` records what it receives on stdin, so the tests can assert that
the private key reaches ``gh secret set`` and nowhere else.  The published key
is served through a ``file://`` URL.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'rotate-apt-key.sh'
OLD_HASH = '0' * 64
GH_STUB = """#!/bin/bash
echo "$*" >"$GH_ARGS"
cat >"$GH_STDIN"
"""


@pytest.fixture(name='env')
def fixture_env(tmp_path: Path) -> dict[str, str]:
    """Environment with a stub gh first on PATH and a fake repository root."""
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    gh = bindir / 'gh'
    gh.write_text(GH_STUB)
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    repo = tmp_path / 'repo'
    repo.mkdir()
    for name in ('Containerfile', 'Containerfile.minimal'):
        (repo /
         name).write_text(f'FROM x\nARG BOOTC_GPG_SHA256={OLD_HASH}\nRUN y\n')
    return {
        **os.environ,
        'PATH': f'{bindir}:{os.environ["PATH"]}',
        'GH_ARGS': str(tmp_path / 'gh.args'),
        'GH_STDIN': str(tmp_path / 'gh.stdin'),
        'ROOT_DIR': str(repo),
        'WAIT_ATTEMPTS': '2',
        'WAIT_SECONDS': '0',
    }


def _run(args: list[str], env: dict[str,
                                    str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(SCRIPT), *args],
                          check=False,
                          capture_output=True,
                          text=True,
                          env=env,
                          timeout=120)


def test_rotate_sends_private_key_only_to_gh(env: dict[str, str]) -> None:
    """The private key goes to `gh secret set` and never to stdout/stderr."""
    result = _run(['rotate'], env)
    assert result.returncode == 0, result.stderr
    assert Path(env['GH_ARGS']).read_text().strip() == 'secret set APT_GPG_KEY'
    secret = Path(env['GH_STDIN']).read_text()
    assert 'BEGIN PGP PRIVATE KEY BLOCK' in secret
    body = ''.join(secret.splitlines()[3:-2])
    assert body and body not in result.stdout + result.stderr
    assert re.fullmatch(r'[0-9A-F]{40}', result.stdout.strip())
    assert 'PRIVATE' not in result.stdout + result.stderr


def _publish(tmp_path: Path, secret: str) -> tuple[Path, str]:
    """Derive the public key file and fingerprint from an exported secret."""
    # Keep the path short: gpg-agent sockets cannot exceed ~100 characters.
    home = Path(tempfile.mkdtemp(dir='/tmp'))
    genv = {**os.environ, 'GNUPGHOME': str(home)}
    imp = subprocess.run([
        'gpg', '--batch', '--quiet', '--pinentry-mode', 'loopback',
        '--passphrase', '', '--import'
    ],
                         input=secret,
                         text=True,
                         check=False,
                         env=genv,
                         capture_output=True)
    assert imp.returncode == 0, imp.stderr
    pub = subprocess.run(['gpg', '--batch', '--armor', '--export'],
                         check=True,
                         env=genv,
                         capture_output=True,
                         text=True).stdout
    listing = subprocess.run(['gpg', '--batch', '--with-colons', '--list-keys'],
                             check=True,
                             env=genv,
                             capture_output=True,
                             text=True).stdout
    fpr = next(
        l.split(':')[9] for l in listing.splitlines() if l.startswith('fpr:')
    )
    subprocess.run(['gpgconf', '--kill', 'gpg-agent'], env=genv, check=False)
    shutil.rmtree(home, ignore_errors=True)
    key_file = tmp_path / 'gpg.key'
    key_file.write_text(pub)
    return key_file, fpr


def test_publish_hash_updates_both_containerfiles(
    env: dict[str, str], tmp_path: Path
) -> None:
    """The hash of the served key replaces the pinned one in both files."""
    assert _run(['rotate'], env).returncode == 0
    key_file, fpr = _publish(tmp_path, Path(env['GH_STDIN']).read_text())
    env['KEY_URL'] = key_file.as_uri()
    result = _run(['publish-hash', fpr], env)
    assert result.returncode == 0, result.stderr
    digest = hashlib.sha256(key_file.read_bytes()).hexdigest()
    for name in ('Containerfile', 'Containerfile.minimal'):
        text = (Path(env['ROOT_DIR']) / name).read_text()
        assert f'ARG BOOTC_GPG_SHA256={digest}\n' in text
        assert OLD_HASH not in text
        assert text.startswith('FROM x\n') and text.endswith('RUN y\n')


def test_publish_hash_refuses_a_different_key(
    env: dict[str, str], tmp_path: Path
) -> None:
    """A served key with another fingerprint leaves the pins untouched."""
    assert _run(['rotate'], env).returncode == 0
    key_file, _ = _publish(tmp_path, Path(env['GH_STDIN']).read_text())
    env['KEY_URL'] = key_file.as_uri()
    result = _run(['publish-hash', 'A' * 40], env)
    assert result.returncode != 0
    assert OLD_HASH in (Path(env['ROOT_DIR']) / 'Containerfile').read_text()


def test_publish_hash_rejects_bad_fingerprint(env: dict[str, str]) -> None:
    """A malformed fingerprint argument is refused up front."""
    assert _run(['publish-hash', 'nope'], env).returncode != 0
