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
    'kernel-src' / 'modprobe'
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
    derive_cmd: str = '',
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the real script in a sandbox.

    Args:
        tmp_path: Sandbox directory for the state and the payload.
        *args: Command line of the script.
        payload: Whether the payload directory is populated (from the
            build-embedded copies).
        derive_cmd: The DC_GPU_DERIVE_CMD override (a compose stand-in).
        extra_env: Additional environment (engine selection, tool dir).

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
        GPU_SET_APT_DIR=str(tmp_path / 'apt'),
        # the test process itself may carry the engine env of another lane
        DC_GPU_DERIVE_ENGINE='podman',
        DC_APT2OSTREE='',
    )
    if derive_cmd:
        env['DC_GPU_DERIVE_CMD'] = derive_cmd
    if extra_env:
        env.update(extra_env)
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
    for pkg in ('libcuda1', 'gpu-gaming-nvidia', 'kflav', '"$oset"', '+r1nv'):
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


# ---------------------------------------------------------------------------
# The apt2ostree derive engine (owner arbitration 2026-11-04): the tool comes
# from the upstream repository at live-build. The tests stub the small part of
# its API the driver touches and the ostree/ninja binaries on PATH, and pin
# the generated lockfile/driver and the ref plumbing; the real-tool chain
# (upstream d5c31086 + ostree + ninja, no GPU) is proven out of band.
# ---------------------------------------------------------------------------

A2O_INIT_STUB = '''
"""Stub of the upstream apt2ostree package for the driver-lane tests."""
class Apt:
    def __init__(self, ninja):
        self._ninja = ninja
    def build_image(self, lockfile, packages, apt_sources,
                    unpack_only=False, **kwargs):
        assert lockfile == 'nvidia.lock'
        assert unpack_only, 'the NVIDIA layer is the unpack combine'
        return _StubRef('ostree/refs/heads/deb/images/nvidia.lock/unpacked')
class _StubRef:
    def __init__(self, filename):
        self.filename = filename
class Ninja:
    def __init__(self, argv, standalone=True):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def variable(self, key, value):
        assert key == 'ostree_repo' and value == 'ostree'
    def default(self, filename):
        print('default', filename)
'''

A2O_APT_STUB = '''
"""Stub of apt2ostree.apt for the driver-lane tests."""
from collections import namedtuple

AptSource = namedtuple(
    'AptSource', 'architecture distribution archive_url components keyrings')
'''

A2O_OSTREE_STUB = '''
"""Stub of apt2ostree.ostree."""
class _StubRef:
    def __init__(self, filename):
        self.filename = filename
class ostree_combine:
    @staticmethod
    def build(ninja, inputs, branch, **kwargs):
        import os
        state = os.environ['GPU_SET_STATE_DIR']
        os.makedirs(state, exist_ok=True)
        path = state + '/combine.log'
        with open(path, 'w', encoding='utf-8') as handle:
            print(inputs, branch, file=handle)
        return _StubRef('ostree/refs/heads/' + branch)
'''


def a2o_tool(tmp_path: Path) -> Path:
    """Write the stub of the upstream tool package.

    Args:
        tmp_path: Sandbox directory.

    Returns:
        The tool dir to hand to DC_APT2OSTREE.
    """
    tool = tmp_path / 'tool'
    (tool / 'apt2ostree').mkdir(parents=True, exist_ok=True)
    (tool / 'apt2ostree' /
     '__init__.py').write_text(A2O_INIT_STUB, encoding='utf-8')
    (tool / 'apt2ostree' /
     'ostree.py').write_text(A2O_OSTREE_STUB, encoding='utf-8')
    (tool / 'apt2ostree' / 'apt.py').write_text(A2O_APT_STUB, encoding='utf-8')
    return tool


def a2o_path(tmp_path: Path) -> str:
    """Put the ostree and ninja stand-ins first on the process PATH.

    Args:
        tmp_path: Sandbox directory.

    Returns:
        The previous PATH value to restore afterwards.
    """
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir(exist_ok=True)
    ninja = bin_dir / 'ninja'
    ninja.write_text(
        '\n'.join([
            '#!/bin/sh',
            'echo ninja "$@" >> "' + str(tmp_path) + '/state/ninja.log"',
        ]) + '\n',
        encoding='utf-8'
    )
    ostree = bin_dir / 'ostree'
    ostree.write_text(
        '\n'.join([
            '#!/bin/sh',
            'echo "ostree $@" >> "' + str(tmp_path) + '/state/ostree.log"',
            'for arg in "$@"; do',
            '    case "$arg" in */refs/heads*) mkdir -p "$arg" ;; esac',
            'done',
            # ls of /usr/lib/modules: the base deployment of the fixture
            # carries one kernel of a flavour-suffixed release.
            'for arg in "$@"; do',
            '    case "$arg" in */usr/lib/modules) '
            'echo "d00755 0 0 0 /usr/lib/modules/7.2.15-x64v2-xanmod1" ;; esac',
            'done',
            'exit 0',
        ]) + '\n',
        encoding='utf-8'
    )
    ninja.chmod(0o755)
    ostree.chmod(0o755)
    previous = os.environ['PATH']
    os.environ['PATH'] = str(bin_dir) + ':' + previous
    return previous


def a2o_env(tmp_path: Path) -> dict[str, str]:
    """The environment of the apt2ostree engine tests.

    Args:
        tmp_path: Sandbox directory.

    Returns:
        The environment additions handed to `run`.
    """
    return {
        'DC_GPU_DERIVE_ENGINE': 'apt2ostree',
        'DC_APT2OSTREE': str(a2o_tool(tmp_path)),
    }


def a2o_debs(tmp_path: Path) -> Path:
    """Build the NVIDIA user-space and set debs of the sandbox.

    Args:
        tmp_path: Sandbox directory.

    Returns:
        The apt cache directory carrying the debs.
    """
    cache = tmp_path / 'apt' / 'apt'
    cache.mkdir(parents=True, exist_ok=True)
    root = tmp_path / 'debroot'
    for pkg in (
        'libcuda1',
        'nvidia-driver-libs',
        'nvidia-smi',
        'nvidia-persistenced',
        'nvidia-opencl-icd',
        'nvidia-vulkan-icd',
        'firmware-nvidia-gsp',
        'gpu-gaming-nvidia-x64v2',
    ):
        (root / pkg / 'DEBIAN').mkdir(parents=True)
        (root / pkg / 'DEBIAN' / 'control').write_text(
            f'Package: {pkg}\nVersion: 580.95.05-1\n'
            'Architecture: amd64\nMaintainer: t <t@t>\n'
            f'Description: chain proof {pkg}\n',
            encoding='utf-8'
        )
        libdir = root / pkg / 'usr' / 'lib' / 'x86_64-linux-gnu'
        libdir.mkdir(parents=True)
        (libdir / (pkg + '.so.1')).write_text('bin', encoding='utf-8')
        subprocess.run([
            'dpkg-deb', '--build', '-Zxz', '--root-owner-group',
            str(root / pkg),
            str(cache / (pkg + '_580.95.05-1_amd64.deb'))
        ],
                       check=True,
                       capture_output=True)
    return cache


def test_derive_apt2ostree_requires_the_tool(tmp_path: Path) -> None:
    """Without the upstream tool the derive refuses and names the fetch.

    Args:
        tmp_path: Sandbox directory.
    """
    result = run(
        tmp_path,
        'derive',
        'gpu-gaming-nvidia',
        extra_env={
            'DC_GPU_DERIVE_ENGINE': 'apt2ostree',
            'DC_APT2OSTREE': str(tmp_path / 'no-such'),
        }
    )
    assert result.returncode == 1
    assert 'stb-tester/apt2ostree' in result.stderr
    assert 'never hosted' in result.stderr


def test_derive_rejects_open_sets_and_unknown_engines(
    tmp_path: Path,
) -> None:
    """The engine refuses an open set; an unknown engine is refused too.

    Args:
        tmp_path: Sandbox directory.
    """
    result = run(
        tmp_path,
        'derive',
        'gpu-ia',
        'reg/base',
        extra_env={
            'DC_GPU_DERIVE_ENGINE': 'apt2ostree',
            'DC_APT2OSTREE': str(a2o_tool(tmp_path)),
        }
    )
    assert result.returncode == 1
    result = run(
        tmp_path,
        'derive',
        'gpu-gaming-nvidia',
        'reg/base',
        extra_env={
            'DC_GPU_DERIVE_ENGINE': 'weird',
        }
    )
    assert result.returncode == 1
    assert 'unknown derive engine' in result.stderr


def test_derive_apt2ostree_composes_the_nvidia_deployment(
    tmp_path: Path,
) -> None:
    """The engine composes the base tree plus the NVIDIA deb layer.

    The tool sits at its upstream-shaped dir, the debs are the cached ones,
    the combine puts the NVIDIA layer FIRST so a conflict yields to the base
    tree (the dpkg status of the base is never wiped), and the derived ref is
    pulled into the base repo and recorded.

    Args:
        tmp_path: Sandbox directory.
    """
    cache = a2o_debs(tmp_path)
    repo = tmp_path / 'base-repo'
    (repo / 'refs' / 'heads').mkdir(parents=True)
    previous = a2o_path(tmp_path)
    try:
        result = run(
            tmp_path,
            'derive',
            'gpu-gaming-nvidia',
            'ostree:' + str(repo) + '#os/base',
            extra_env=a2o_env(tmp_path)
        )
    finally:
        os.environ['PATH'] = previous
    assert result.returncode == 0, result.stderr
    expected = (
        'ostree:' + str(repo) + '#install/nvidia/gpu-gaming-nvidia/derived'
    )
    assert result.stdout.strip() == expected
    work = cache.parent / 'derive-a2o' / 'gpu-gaming-nvidia'
    lockfile = (work / 'nvidia.lock').read_text(encoding='utf-8')
    assert 'Package: gpu-gaming-nvidia-x64v2' in lockfile
    assert 'Version: 580.95.05-1' in lockfile
    assert 'SHA256: ' in lockfile
    driver = (work / 'configure.py').read_text(encoding='utf-8')
    assert str(a2o_tool(tmp_path)) in driver
    assert "'libcuda1'" in driver
    combine = (tmp_path / 'state' / 'combine.log').read_text(encoding='utf-8')
    assert combine.find('deb/images/nvidia.lock/unpacked'
                        ) < combine.find('os/base')
    log = (tmp_path / 'state' / 'ostree.log').read_text(encoding='utf-8')
    assert 'pull-local' in log
