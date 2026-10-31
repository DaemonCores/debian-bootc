"""Unit tests for the installer helper ``nvidia-eula-stage``.

The script is run AS IS through ``subprocess`` with the ``NVIDIA_EULA_FILE`` and
``NVIDIA_EULA_STATE_DIR`` environment variables pointing at the sandbox, so
coverage measures the real source file. A stub ``lspci`` sits first on ``PATH``
so both the NVIDIA-detected and the no-GPU branches run without real hardware.

Wiki contract: ``DaemonCores-VE.wiki/GPU-Support.md`` (install-time EULA flow) —
the shipped EULA file must stay the verbatim consent paragraph of that page.
"""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'usr' /
    'libexec' / 'debian-bootc' / 'nvidia-eula-stage'
)
NVIDIA_EULA = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'usr' /
    'share' / 'debian-bootc' / 'nvidia-eula.txt'
)

LSPCI_NVIDIA = """\
#!/bin/sh
echo "01:00.0 3D controller: NVIDIA Corporation GA106 [GeForce RTX 3060]"
"""
LSPCI_NONE = "#!/bin/sh\nexit 0\n"


def load() -> ModuleType:
    """Import nvidia-eula-stage as a single module.

    Returns:
        The freshly executed ``nvidia_eula_stage`` module.
    """
    spec = importlib.util.spec_from_file_location(
        'nvidia_eula_stage',
        SCRIPT,
        loader=importlib.machinery.SourceFileLoader(
            'nvidia_eula_stage', str(SCRIPT)
        ),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(
    tmp_path: Path,
    *args: str,
    stdin: str = '',
    lspci: str = LSPCI_NVIDIA,
) -> subprocess.CompletedProcess:
    """Run the real script against a sandbox environment.

    Args:
        tmp_path: Scratch directory holding the sandbox.
        *args: Command line of the script (variadic).
        stdin: Text fed on stdin.
        lspci: Body of the stub ``lspci``.

    Returns:
        The completed process.
    """
    bindir = tmp_path / 'bin'
    bindir.mkdir(exist_ok=True)
    stub = bindir / 'lspci'
    stub.write_text(lspci)
    stub.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f'{bindir}:{os.environ["PATH"]}',
        NVIDIA_EULA_FILE=str(tmp_path / 'nvidia-eula.txt'),
        NVIDIA_EULA_STATE_DIR=str(tmp_path / 'run' / 'bootc-installer'),
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def state_path(tmp_path: Path) -> Path:
    """Return the acceptance-flag path inside the sandbox.

    Args:
        tmp_path: Sandbox root.

    Returns:
        The flag file path.
    """
    return tmp_path / 'run' / 'bootc-installer' / 'nvidia-eula-accepted'


@pytest.fixture
def eula_sandbox(tmp_path: Path) -> Path:
    """Drop the EULA text into the sandbox.

    Args:
        tmp_path: Scratch directory.

    Returns:
        The sandbox root.
    """
    (tmp_path /
     'nvidia-eula.txt').write_text('EULA-TEXT-VERBATIM\n', encoding='utf-8')
    return tmp_path


def test_probe_detected(tmp_path: Path) -> None:
    """The probe exits 0 and reports the model when lspci sees NVIDIA.

    Args:
        tmp_path: Scratch directory.
    """
    result = run(tmp_path, 'probe')
    assert result.returncode == 0, result.stderr
    assert 'RTX 3060' in result.stdout


def test_probe_no_gpu(tmp_path: Path) -> None:
    """Without an NVIDIA device the probe exits 1 and stays silent.

    Args:
        tmp_path: Scratch directory.
    """
    result = run(tmp_path, 'probe', lspci=LSPCI_NONE)
    assert result.returncode == 1
    assert result.stdout == ''


def test_text_prints_eula(eula_sandbox: Path) -> None:
    """The text command prints the shipped EULA verbatim.

    Args:
        eula_sandbox: Sandbox directory with the EULA text.
    """
    result = run(eula_sandbox, 'text')
    assert result.returncode == 0, result.stderr
    assert result.stdout == 'EULA-TEXT-VERBATIM\n'


def test_consent_interactive_requires_exact_accept(
    eula_sandbox: Path,
) -> None:
    """Interactive consent accepts only the exact word ``ACCEPT``.

    Args:
        eula_sandbox: Sandbox directory with the EULA text.
    """
    assert run(eula_sandbox, 'consent', stdin='accept\n').returncode != 0
    assert not state_path(eula_sandbox).exists()
    assert run(eula_sandbox, 'consent', stdin='ACCEPT\n').returncode == 0
    assert state_path(eula_sandbox).exists()


def test_consent_explicit_flag(eula_sandbox: Path) -> None:
    """``--accept`` records the flag non-interactively.

    Args:
        eula_sandbox: Sandbox directory with the EULA text.
    """
    result = run(eula_sandbox, 'consent', '--accept')
    assert result.returncode == 0, result.stderr
    assert state_path(eula_sandbox).exists()


def usage_path(root: Path) -> Path:
    """Locate the recorded usage file of a sandbox.

    Args:
        root: Sandbox directory.

    Returns:
        The usage state path.
    """
    return state_path(root).with_name('gpu-usage')


def test_usage_ia_with_nvidia_requires_consent(tmp_path: Path) -> None:
    """The ia profile with an NVIDIA GPU present is refused before consent.

    Args:
        tmp_path: Scratch directory.
    """
    result = run(tmp_path, 'usage', 'ia')
    assert result.returncode == 1
    assert not usage_path(tmp_path).exists()


def test_usage_ia_with_consent_is_recorded(tmp_path: Path) -> None:
    """Consent lets the ia profile be recorded.

    Args:
        tmp_path: Scratch directory.
    """
    (tmp_path / 'nvidia-eula.txt').write_text('EULA\n', encoding='utf-8')
    assert run(tmp_path, 'consent', '--accept').returncode == 0
    result = run(tmp_path, 'usage', 'ia')
    assert result.returncode == 0, result.stderr
    assert usage_path(tmp_path).read_text(encoding='utf-8') == 'ia\n'


def test_usage_ia_without_nvidia_needs_no_consent(tmp_path: Path) -> None:
    """Another vendor's GPU running ia never needs the NVIDIA EULA.

    Args:
        tmp_path: Scratch directory.
    """
    result = run(tmp_path, 'usage', 'ia', lspci=LSPCI_NONE)
    assert result.returncode == 0, result.stderr
    assert usage_path(tmp_path).read_text(encoding='utf-8') == 'ia\n'


@pytest.mark.parametrize('usage', ['gaming', 'auto'])
def test_usage_other_profiles_need_no_consent(
    tmp_path: Path, usage: str
) -> None:
    """Gaming and auto are recorded without consent even with NVIDIA present.

    Args:
        tmp_path: Scratch directory.
        usage: The profile under test.
    """
    result = run(tmp_path, 'usage', usage)
    assert result.returncode == 0, result.stderr
    assert usage_path(tmp_path).read_text(encoding='utf-8') == f'{usage}\n'


def test_usage_unknown_refused(tmp_path: Path) -> None:
    """An unknown profile is refused and nothing is recorded.

    Args:
        tmp_path: Scratch directory.
    """
    result = run(tmp_path, 'usage', 'evil')
    assert result.returncode == 1
    assert not usage_path(tmp_path).exists()


def test_usage_error(tmp_path: Path) -> None:
    """No argument or an unknown command exits with status 1.

    Args:
        tmp_path: Scratch directory.
    """
    assert run(tmp_path).returncode == 1
    assert run(tmp_path, 'bogus').returncode == 1


def test_text_missing_file(tmp_path: Path) -> None:
    """A missing EULA file fails with a clear error, not a traceback.

    Args:
        tmp_path: Scratch directory without the EULA text.
    """
    result = run(tmp_path, 'text')
    assert result.returncode == 1
    assert 'missing' in result.stderr


def test_select_bad_recipe(tmp_path: Path) -> None:
    """A recipe without an image list fails instead of crashing.

    Args:
        tmp_path: Scratch directory.
    """
    target = tmp_path / 'recipe.json'
    target.write_text('{"imgref": "x"}', encoding='utf-8')
    result = run(tmp_path, 'select', str(target), 'reg/x:latest_amd64')
    assert result.returncode == 1


def test_wiki_parity() -> None:
    """The shipped EULA keeps quoting the wiki consent paragraph.

    Skipped when the wiki clone is not a sibling of the repository: CI runs
    standalone while local runs re-verify the parity.
    """
    wiki = Path(__file__).resolve().parents[3] / 'DaemonCores-VE.wiki'
    page = wiki / 'GPU-Support.md'
    if not page.exists():
        pytest.skip('wiki clone not present')
    shipped = NVIDIA_EULA.read_text(encoding='utf-8')
    source = page.read_text(encoding='utf-8')
    quote = ''.join(
        line[2:] if line.startswith('> ') else ''
        for line in source.splitlines(True)
    )
    assert 'nvidia-license' in source
    assert shipped.strip() == quote.strip()
