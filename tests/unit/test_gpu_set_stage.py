"""Unit tests for ``gpu-set-stage``, the install-time GPU module set helper.

The helper is an installer-lane script: the tests run it as a subprocess with
environment-injected state/payload directories so no privileged path is touched.
"""

import os
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'usr' /
    'libexec' / 'debian-bootc' / 'gpu-set-stage.py'
)
MODPROBE_DIR = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'kernel' / 'modules' / 'gpu' / 'modprobe'
)
PAYLOAD_SRC = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'usr' /
    'share' / 'debian-bootc' / 'gpu-sets'
)
SET_NAMES = (
    'gpu-ia',
    'gpu-gaming',
    'gpu-ia-nvidia',
    'gpu-gaming-nvidia',
)


def run(
    tmp_path: Path,
    *args: str,
    payload: bool = True,
    derive_cmd: str = ''
) -> subprocess.CompletedProcess:
    """Run the real script in a sandbox.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
        *args: Command line of the script.
        payload: Whether the payload directory is populated (from the
            build-embedded copies).
        derive_cmd: The DC_GPU_DERIVE_CMD override (a compose stand-in).

    Returns:
        The completed process.
    """
    state = tmp_path / 'state'
    payload_dir = tmp_path / 'payload'
    if payload:
        payload_dir.mkdir(parents=True, exist_ok=True)
        for conf in PAYLOAD_SRC.iterdir():
            target = payload_dir / conf.name
            target.write_text(
                conf.read_text(encoding='utf-8'), encoding='utf-8'
            )
    env = dict(
        os.environ,
        GPU_SET_STATE_DIR=str(state),
        GPU_SET_PAYLOAD_DIR=str(payload_dir),
        GPU_SET_APT_DIR=str(tmp_path / 'apt')
    )
    if derive_cmd:
        env['DC_GPU_DERIVE_CMD'] = derive_cmd
    return subprocess.run(
        ['python3', str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_sets_lists_the_four_names(tmp_path: Path) -> None:
    """``sets`` prints the four module set names.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
    """
    result = run(tmp_path, 'sets')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == list(SET_NAMES)


def test_set_records_and_status_reads_back(tmp_path: Path) -> None:
    """``set`` stores the choice; ``status`` reads it back.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
    """
    assert run(tmp_path, 'set', 'gpu-gaming-nvidia').returncode == 0
    result = run(tmp_path, 'status')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'gpu-gaming-nvidia'


def test_set_rejects_unknown_name(tmp_path: Path) -> None:
    """An unknown set fails without recording anything.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
    """
    result = run(tmp_path, 'set', 'gpu-evil')
    assert result.returncode == 1
    assert run(tmp_path, 'status').stdout.strip() == ''


def test_install_delivers_the_conf_to_the_target(tmp_path: Path) -> None:
    """``install`` copies the set loader policy into the target root.

    The deb pull cannot succeed in the sandbox (no apt index): the helper still
    delivers the conf and exits 0 with the conf-only note, the documented
    fallback.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
    """
    root = tmp_path / 'target'
    (root / 'usr' / 'lib' / 'modules').mkdir(parents=True)
    (root / 'usr' / 'lib' / 'modules' / '6.14.0-x64v2-xanmod1').mkdir()
    result = run(tmp_path, 'install', 'gpu-gaming', str(root))
    assert result.returncode == 0, result.stderr
    conf = root / 'etc' / 'modprobe.d' / 'dc-gpu-gaming.conf'
    assert conf.is_file(), result.stderr
    source = MODPROBE_DIR / 'dc-gpu-gaming.conf'
    assert conf.read_text(encoding='utf-8'
                          ) == source.read_text(encoding='utf-8')


def test_install_rejects_unknown_set_and_bad_root(tmp_path: Path) -> None:
    """``install`` fails loudly for an unknown set and for a missing root.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
    """
    assert run(tmp_path, 'install', 'gpu-evil', str(tmp_path)).returncode == 1
    assert run(tmp_path, 'install', 'gpu-ia', 'relative/root').returncode == 1


def test_payload_matches_the_build_policy_files() -> None:
    """The shipped conf payload equals the deb policy files verbatim.

    The live image carries copies the delivery falls back to; both sides must
    never diverge (same discipline as the NVIDIA EULA pin).
    """
    for name in (
        'dc-gpu-ia.conf', 'dc-gpu-gaming.conf', 'dc-gpu-ia-nvidia.conf',
        'dc-gpu-gaming-nvidia.conf'
    ):
        assert (PAYLOAD_SRC / name).read_text(
            encoding='utf-8'
        ) == (MODPROBE_DIR / name).read_text(encoding='utf-8')


def test_derive_builds_the_nvidia_containerfile(tmp_path: Path) -> None:
    """``derive`` composes the derived image with the package list.

    The compose stand-in copies the generated Containerfile into a marker
    file and touches the output: the test pins the payload (base ref, the
    signed NVIDIA repo fetch, the nvidia user-space + the -nvidia module
    set) and the recorded derived ref.

    Args:
        tmp_path: Sandbox directory for the state and the compose output.
    """
    tmp = tmp_path / 'derive'
    tmp.mkdir()
    marker = tmp / 'containerfile.saved'
    derive_cmd = (
        f"cp {{CONTAINERFILE}} {marker} && "
        f"printf 'compose done' > {tmp / 'out'}"
    )
    result = run(
        tmp_path,
        'derive',
        'gpu-gaming-nvidia',
        'reg/base:latest_amd64',
        derive_cmd=derive_cmd
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'reg/base:latest_amd64-nvidia'
    saved = marker.read_text(encoding='utf-8')
    assert 'FROM reg/base:latest_amd64' in saved
    assert 'developer.download.nvidia.com' in saved
    assert 'cuda-keyring' in saved
    for pkg in ('libcuda1', 'gpu-gaming-nvidia'):
        assert pkg in saved, pkg
    assert 'requires-eula="nvidia"' in saved
    assert run(tmp_path, 'derived').stdout.strip() == \
        'reg/base:latest_amd64-nvidia'


def test_derive_refuses_open_sets_and_failures(tmp_path: Path) -> None:
    """The open sets are debs, not derived images; a failed compose fails.

    Args:
        tmp_path: Sandbox directory for the state directory.
    """
    result = run(tmp_path, 'derive', 'gpu-ia', 'reg/base')
    assert result.returncode == 1
    failed = tmp_path / 'fail'
    failed.mkdir()
    result = run(
        tmp_path,
        'derive',
        'gpu-ia-nvidia',
        'reg/base',
        derive_cmd=f"exit 3  # {failed}",
    )
    assert result.returncode == 1


def test_base_records_the_install_payload_ref(tmp_path: Path) -> None:
    """``base`` records the payload the derive composes on top of.

    Args:
        tmp_path: Sandbox directory for the state directory.
    """
    assert run(tmp_path, 'base', 'reg/base:latest_amd64').returncode == 0
    result = run(tmp_path, 'derive', 'gpu-gaming-nvidia', derive_cmd='true')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'reg/base:latest_amd64-nvidia'
