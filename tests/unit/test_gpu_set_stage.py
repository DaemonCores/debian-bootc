"""Unit tests for ``gpu-set-stage``, the install-time GPU module set helper.

The helper is an installer-lane script: the tests run it as a subprocess
with environment-injected state/payload directories so no privileged path
is touched.
"""

import os
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' /
    'usr' / 'libexec' / 'debian-bootc' / 'gpu-set-stage'
)
MODPROBE_DIR = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'kernel' / 'modules' / 'gpu' / 'modprobe'
)
PAYLOAD_SRC = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' /
    'usr' / 'share' / 'debian-bootc' / 'gpu-sets'
)
SET_NAMES = (
    'gpu-ia', 'gpu-gaming', 'gpu-ia-nvidia', 'gpu-gaming-nvidia',
)


def run(
    tmp_path: Path, *args: str, payload: bool = True
) -> subprocess.CompletedProcess:
    """Run the real script in a sandbox.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
        *args: Command line of the script.
        payload: Whether the payload directory is populated (from the
            build-embedded copies).

    Returns:
        The completed process.
    """
    state = tmp_path / 'state'
    payload_dir = tmp_path / 'payload'
    if payload:
        payload_dir.mkdir(parents=True, exist_ok=True)
        for conf in PAYLOAD_SRC.iterdir():
            target = payload_dir / conf.name
            target.write_text(conf.read_text(encoding='utf-8'),
                              encoding='utf-8')
    env = dict(os.environ, GPU_SET_STATE_DIR=str(state),
               GPU_SET_PAYLOAD_DIR=str(payload_dir))
    return subprocess.run(
        ['python3', str(SCRIPT), *args],
        env=env, capture_output=True, text=True, check=False,
    )


def test_sets_lists_the_four_names(tmp_path: Path) -> None:
    """``sets`` prints the four module set names."""
    result = run(tmp_path, 'sets')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == list(SET_NAMES)


def test_set_records_and_status_reads_back(tmp_path: Path) -> None:
    """``set`` stores the choice; ``status`` and the recipe agree."""
    assert run(tmp_path, 'set', 'gpu-gaming-nvidia').returncode == 0
    result = run(tmp_path, 'status')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'gpu-gaming-nvidia'


def test_set_rejects_unknown_name(tmp_path: Path) -> None:
    """An unknown set fails without recording anything."""
    result = run(tmp_path, 'set', 'gpu-evil')
    assert result.returncode == 1
    assert run(tmp_path, 'status').stdout.strip() == ''


def test_install_delivers_the_conf_to_the_target(tmp_path: Path) -> None:
    """``install`` copies the set loader policy into the target root.

    The deb pull cannot succeed in the sandbox (no apt index): the helper
    still delivers the conf and exits 0 with the conf-only note, the
    documented fallback.
    """
    root = tmp_path / 'target'
    (root / 'usr' / 'lib' / 'modules').mkdir(parents=True)
    (root / 'usr' / 'lib' / 'modules' / '6.14.0-x64v2-xanmod1').mkdir()
    result = run(tmp_path, 'install', 'gpu-gaming', str(root))
    assert result.returncode == 0, result.stderr
    conf = root / 'etc' / 'modprobe.d' / 'dc-gpu-gaming.conf'
    assert conf.is_file(), result.stderr
    source = MODPROBE_DIR / 'dc-gpu-gaming.conf'
    assert conf.read_text(encoding='utf-8') == source.read_text(
        encoding='utf-8'
    )


def test_install_rejects_unknown_set_and_bad_root(tmp_path: Path) -> None:
    """``install`` fails loudly for an unknown set and for a missing root."""
    assert run(tmp_path, 'install', 'gpu-evil', str(tmp_path)).returncode == 1
    assert run(tmp_path, 'install', 'gpu-ia', 'relative/root').returncode == 1


def test_payload_matches_the_build_policy_files() -> None:
    """The shipped conf payload equals the deb policy files verbatim.

    The live image carries copies the copy payload uses; both sides must
    never diverge (same discipline as the NVIDIA EULA pin).
    """
    for name in ('dc-gpu-ia.conf', 'dc-gpu-gaming.conf',
                 'dc-gpu-ia-nvidia.conf', 'dc-gpu-gaming-nvidia.conf'):
        assert (PAYLOAD_SRC / name).read_text(encoding='utf-8') == (
            MODPROBE_DIR / name).read_text(encoding='utf-8')