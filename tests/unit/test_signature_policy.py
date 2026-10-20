"""Unit tests for ``install-signature-policy``.

The script writes under ``$INSTALL_ROOT`` so it can run outside an image.
"""

import base64
import json
import os
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'src' / 'basepostinstall' / 'usr' /
    'libexec' / 'debian-bootc' / 'install-signature-policy'
)
IMAGE = 'ghcr.io/owner/some-distro'
PEM = '-----BEGIN PUBLIC KEY-----\nMFkw\n-----END PUBLIC KEY-----\n'


def _run(root: Path, image: str,
         key_b64: str) -> subprocess.CompletedProcess[str]:
    """Run ``install-signature-policy`` against a scratch root.

    Args:
        root: Directory used as ``INSTALL_ROOT``.
        image: Image repository the policy applies to.
        key_b64: Base64-encoded public key, possibly empty.

    Returns:
        The completed process, with captured text output.
    """
    return subprocess.run([str(SCRIPT), image, key_b64],
                          check=False,
                          capture_output=True,
                          text=True,
                          env={
                              **os.environ, 'INSTALL_ROOT': str(root)
                          },
                          timeout=10)


def test_policy_requires_the_signature_for_the_image(tmp_path: Path) -> None:
    """The image repository needs a key-signed image, the rest is unchanged.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    result = _run(tmp_path, IMAGE, base64.b64encode(PEM.encode()).decode())
    assert result.returncode == 0, result.stderr
    key = tmp_path / 'etc/pki/containers/image-signing.pub'
    assert key.read_text() == PEM
    policy = json.loads((tmp_path / 'etc/containers/policy.json').read_text())
    assert policy['default'] == [{'type': 'insecureAcceptAnything'}]
    rule, = policy['transports']['docker'][IMAGE]
    assert rule['type'] == 'sigstoreSigned'
    assert rule['keyPath'] == '/etc/pki/containers/image-signing.pub'
    assert rule['signedIdentity'] == {'type': 'matchRepository'}
    registry = (tmp_path /
                'etc/containers/registries.d/image-signature.yaml').read_text()
    assert registry == (
        f'docker:\n  {IMAGE}:\n'
        '    use-sigstore-attachments: true\n'
    )


def test_no_key_ships_no_policy(tmp_path: Path) -> None:
    """Without a public key nothing is written: a policy would block updates.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    result = _run(tmp_path, IMAGE, '')
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


def test_rejects_a_key_that_is_not_pem(tmp_path: Path) -> None:
    """A mangled secret fails the build instead of shipping a broken policy.

    Args:
        tmp_path: Scratch directory used as the install root.
    """
    result = _run(tmp_path, IMAGE, base64.b64encode(b'garbage').decode())
    assert result.returncode != 0
    assert not (tmp_path / 'etc/containers/policy.json').exists()
