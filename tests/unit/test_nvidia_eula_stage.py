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
import io
import json
import os
import runpy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import NoReturn, Protocol, cast

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


class _Api(Protocol):
    """In-process surface of nvidia-eula-stage.

    Attributes:
        EULA_TXT: Default EULA text path.
        STATE_DIR: Directory holding the recorded state.
        STATE_FILE: Acceptance flag path.
        USAGE_FILE: Recorded usage profile path.
        RECIPE_FILE: Installer recipe path.
        USAGES: Accepted usage profiles.
        ACCEPT_WORD: Word required for interactive consent.
        fail: Error reporter that exits.
        probe: GPU probe.
        nvidia_devices: NVIDIA device lister.
        run_lspci: lspci runner.
        eula_text: EULA reader.
        cmd_text: text command.
        cmd_consent: consent command.
        cmd_usage: usage command.
        image_requires_eula: image gate predicate.
        cmd_image: image command.
        main: command-line dispatcher.
    """

    EULA_TXT: Path
    STATE_DIR: Path
    STATE_FILE: Path
    USAGE_FILE: Path
    RECIPE_FILE: Path
    USAGES: tuple[str, ...]
    ACCEPT_WORD: str
    fail: Callable[[str], NoReturn]
    probe: Callable[[], int]
    nvidia_devices: Callable[[], list[str]]
    run_lspci: Callable[[list[str]], str]
    eula_text: Callable[[str], str]
    cmd_text: Callable[[], int]
    cmd_consent: Callable[[bool], int]
    cmd_usage: Callable[[str], int]
    image_requires_eula: Callable[[str], bool]
    cmd_image: Callable[[str], int]
    main: Callable[[], NoReturn]


@pytest.fixture
def api() -> _Api:
    """Load a fresh in-process copy of the helper.

    Returns:
        The typed helper module.
    """
    return cast(_Api, load())


def run(
    tmp_path: Path,
    *args: str,
    stdin: str = '',
    lspci: str = LSPCI_NVIDIA,
) -> subprocess.CompletedProcess[str]:
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
    _ = stub.write_text(lspci)
    stub.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f'{bindir}:{os.environ["PATH"]}',
        NVIDIA_EULA_FILE=str(tmp_path / 'nvidia-eula.txt'),
        NVIDIA_EULA_STATE_DIR=str(tmp_path / 'run' / 'bootc-installer'),
        INSTALLER_RECIPE_FILE=str(tmp_path / 'recipe.json'),
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
    _ = (tmp_path / 'nvidia-eula.txt'
         ).write_text('EULA-TEXT-VERBATIM\n', encoding='utf-8')
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


def test_usage_ia_never_needs_consent(tmp_path: Path) -> None:
    """The ia profile is recorded without consent, NVIDIA GPU or not.

    Args:
        tmp_path: Scratch directory.
    """
    for lspci in (LSPCI_NVIDIA, LSPCI_NONE):
        result = run(tmp_path, 'usage', 'ia', lspci=lspci)
        assert result.returncode == 0, result.stderr
        assert usage_path(tmp_path).read_text(encoding='utf-8') == 'ia\n'


@pytest.mark.parametrize('usage', ['gaming', 'auto'])
def test_usage_other_profiles_are_recorded(tmp_path: Path, usage: str) -> None:
    """Gaming and auto are recorded.

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
    _ = target.write_text('{"imgref": "x"}', encoding='utf-8')
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


RECIPE = {
    'images': [
        {
            'imgref': 'reg/x:latest_amd64'
        },
        {
            'imgref': 'reg/x:nvidia_amd64',
            'eula': 'nvidia'
        },
    ]
}


def write_recipe(root: Path, data: object = RECIPE) -> None:
    """Write the installer recipe of a sandbox.

    Args:
        root: Sandbox root.
        data: JSON-serialisable recipe content.
    """
    _ = (root / 'recipe.json').write_text(json.dumps(data), encoding='utf-8')


def test_image_with_eula_is_refused_before_consent(tmp_path: Path) -> None:
    """The entry carrying ``eula`` is refused until the license is accepted.

    Args:
        tmp_path: Scratch directory.
    """
    write_recipe(tmp_path)
    result = run(tmp_path, 'image', 'reg/x:nvidia_amd64')
    assert result.returncode == 1
    assert 'not accepted' in result.stderr


def test_image_with_eula_passes_after_consent(tmp_path: Path) -> None:
    """Once the license is recorded the entry carrying ``eula`` passes.

    Args:
        tmp_path: Scratch directory.
    """
    write_recipe(tmp_path)
    assert run(tmp_path, 'consent', '--accept').returncode == 0
    result = run(tmp_path, 'image', 'reg/x:nvidia_amd64')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('imgref', ['reg/x:latest_amd64', 'other/custom:1'])
def test_other_images_need_no_license(tmp_path: Path, imgref: str) -> None:
    """Images without ``eula``, and images the recipe does not list, pass.

    Args:
        tmp_path: Scratch directory.
        imgref: Image reference under test.
    """
    write_recipe(tmp_path)
    result = run(tmp_path, 'image', imgref)
    assert result.returncode == 0, result.stderr


def test_image_with_unreadable_recipe_is_refused(tmp_path: Path) -> None:
    """A missing recipe never lets the gate pass silently.

    Args:
        tmp_path: Scratch directory.
    """
    result = run(tmp_path, 'image', 'reg/x:nvidia_amd64')
    assert result.returncode == 1
    assert 'recipe unreadable' in result.stderr


def test_script_imports_in_process() -> None:
    """The helper imports as a module and carries its command surface."""
    module = load()
    assert module.__name__ == 'nvidia_eula_stage'
    assert 'probe' in (module.__doc__ or '')


def test_wiki_parity_skips_without_the_clone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The parity check is skipped when the wiki clone is absent.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory standing in for the wiki tree.
    """
    real = tmp_path / 'elsewhere'
    _ = real.write_text('x', encoding='utf-8')
    assert _wiki_page_absent(real)
    monkeypatch.setattr(Path, 'exists', _wiki_page_absent)
    with pytest.raises(pytest.skip.Exception):
        test_wiki_parity()


def _point_state(api: _Api, monkeypatch: pytest.MonkeyPatch,
                 root: Path) -> tuple[Path, Path]:
    """Redirect the recorded state of the helper into a sandbox.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        root: Sandbox directory.

    Returns:
        The acceptance flag and usage profile paths.
    """
    state = root / 'state'
    accepted = state / 'nvidia-eula-accepted'
    usage = state / 'gpu-usage'
    monkeypatch.setattr(api, 'STATE_DIR', state)
    monkeypatch.setattr(api, 'STATE_FILE', accepted)
    monkeypatch.setattr(api, 'USAGE_FILE', usage)
    return accepted, usage


def _write_recipe(
    api: _Api, monkeypatch: pytest.MonkeyPatch, root: Path, content: str
) -> None:
    """Write the installer recipe of a sandbox and point the helper at it.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        root: Sandbox directory.
        content: Raw recipe file content.
    """
    path = root / 'recipe.json'
    _ = path.write_text(content, encoding='utf-8')
    monkeypatch.setattr(api, 'RECIPE_FILE', path)


_REAL_EXISTS = Path.exists


def _wiki_page_absent(path: Path) -> bool:
    """Pretend the wiki page is absent.

    Args:
        path: The path being tested.

    Returns:
        False for the wiki page, the real answer otherwise.
    """
    if path.name == 'GPU-Support.md':
        return False
    return _REAL_EXISTS(path)


def _no_devices() -> list[str]:
    """Return no device.

    Returns:
        An empty device list.
    """
    return []


class _LspciRecorder:
    """Record lspci queries and answer the first one with two lines."""

    def __init__(self) -> None:
        """Initialise the recorded calls."""
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> str:
        """Record a query and return the fake stdout.

        Args:
            args: The lspci arguments.

        Returns:
            Two lines once, then nothing.
        """
        self.calls.append(args)
        return 'first\n\nsecond\n' if len(self.calls) == 1 else ''


def _missing_eula() -> NoReturn:
    """Raise the error of an unreadable EULA file.

    Raises:
        OSError: always.
    """
    raise OSError('gone')


def _needs_license(imgref: str) -> bool:
    """Report every image as licensed.

    Args:
        imgref: Image reference under test.

    Returns:
        Always True.
    """
    _ = imgref
    return True


def _open_image(imgref: str) -> bool:
    """Report no image as licensed.

    Args:
        imgref: Image reference under test.

    Returns:
        Always False.
    """
    _ = imgref
    return False


def _consent_status(accept: bool) -> int:
    """Record the forwarded consent flag.

    Args:
        accept: The flag passed by the dispatcher.

    Returns:
        The exit status.
    """
    assert accept is True
    return 3


def _usage_status(usage: str) -> int:
    """Record the forwarded usage profile.

    Args:
        usage: The profile passed by the dispatcher.

    Returns:
        The exit status.
    """
    assert usage == 'ia'
    return 4


def _image_status(imgref: str) -> int:
    """Record the forwarded image reference.

    Args:
        imgref: The reference passed by the dispatcher.

    Returns:
        The exit status.
    """
    assert imgref == 'reg/x:latest_amd64'
    return 6


def test_probe_prints_the_detected_devices(
    api: _Api, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """The in-process probe prints every device and returns 0.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capture fixture.
    """
    monkeypatch.setattr(api, 'nvidia_devices', lambda: ['dev-a', 'dev-b'])
    assert api.probe() == 0
    assert capsys.readouterr().out == 'dev-a\ndev-b\n'


def test_probe_without_a_device_fails_quietly(
    api: _Api, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """Without a device the in-process probe returns 1 and prints nothing.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capture fixture.
    """
    monkeypatch.setattr(api, 'nvidia_devices', _no_devices)
    assert api.probe() == 1
    assert capsys.readouterr().out == ''


def test_nvidia_devices_reads_both_pci_classes(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both lspci class queries run and blank lines are dropped.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
    """
    recorder = _LspciRecorder()
    monkeypatch.setattr(api, 'run_lspci', recorder)
    assert api.nvidia_devices() == ['first', 'second']
    assert recorder.calls == [
        ['lspci', '-d', '10de::0300'],
        ['lspci', '-d', '10de::0380'],
    ]


def test_run_lspci_handles_success_failure_and_absence(api: _Api) -> None:
    """A zero status keeps stdout; a failure or a missing tool is empty.

    Args:
        api: Loaded helper module.
    """
    assert api.run_lspci(['echo', 'hi']) == 'hi\n'
    assert api.run_lspci(['false']) == ''
    assert api.run_lspci(['dc-no-such-lspci-binary']) == ''


def test_eula_text_reads_the_file(api: _Api, tmp_path: Path) -> None:
    """The reader returns the file content verbatim.

    Args:
        api: Loaded helper module.
        tmp_path: Scratch directory.
    """
    path = tmp_path / 'eula.txt'
    _ = path.write_text('TEXT\n', encoding='utf-8')
    assert api.eula_text(str(path)) == 'TEXT\n'


def test_cmd_text_prints_the_eula(
    api: _Api, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """The text command writes the EULA and succeeds.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capture fixture.
    """
    monkeypatch.setattr(api, 'eula_text', lambda: 'TEXT')
    assert api.cmd_text() == 0
    assert capsys.readouterr().out == 'TEXT'


def test_cmd_text_fails_without_the_file(
    api: _Api, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """An unreadable EULA fails through the error reporter.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capture fixture.
    """
    monkeypatch.setattr(api, 'eula_text', _missing_eula)
    with pytest.raises(SystemExit) as raised:
        _ = api.cmd_text()
    assert raised.value.code == 1
    assert 'EULA text missing: gone' in capsys.readouterr().err


def test_cmd_consent_interactive_accepts_the_exact_word(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """The interactive flow needs the exact ACCEPT word.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
        capsys: Pytest capture fixture.
    """
    accepted, _ = _point_state(api, monkeypatch, tmp_path)
    monkeypatch.setattr(api, 'eula_text', lambda: 'TEXT')
    monkeypatch.setattr(sys, 'stdin', io.StringIO('ACCEPT\n'))
    assert api.cmd_consent(False) == 0
    assert accepted.read_text(encoding='utf-8') == 'accepted-at-install\n'
    assert capsys.readouterr().out.startswith('TEXT')


def test_cmd_consent_interactive_refuses_other_input(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """Any other word leaves the license unaccepted.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
        capsys: Pytest capture fixture.
    """
    accepted, _ = _point_state(api, monkeypatch, tmp_path)
    monkeypatch.setattr(api, 'eula_text', lambda: 'TEXT')
    monkeypatch.setattr(sys, 'stdin', io.StringIO('accept\n'))
    assert api.cmd_consent(False) == 1
    assert not accepted.exists()
    assert 'EULA not accepted' in capsys.readouterr().err


def test_cmd_consent_flag_records_without_reading(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The --accept flag records the consent without stdin or EULA text.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    accepted, _ = _point_state(api, monkeypatch, tmp_path)
    assert api.cmd_consent(True) == 0
    assert accepted.is_file()


def test_cmd_consent_fails_without_the_eula(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The interactive flow reports a missing EULA text and exits.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    _ = _point_state(api, monkeypatch, tmp_path)
    monkeypatch.setattr(api, 'eula_text', _missing_eula)
    with pytest.raises(SystemExit) as raised:
        _ = api.cmd_consent(False)
    assert raised.value.code == 1


def test_cmd_usage_records_a_known_profile(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A known usage profile is written verbatim.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    _, usage = _point_state(api, monkeypatch, tmp_path)
    assert api.cmd_usage('ia') == 0
    assert usage.read_text(encoding='utf-8') == 'ia\n'


def test_cmd_usage_rejects_an_unknown_profile(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown profile fails without recording anything.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
        capsys: Pytest capture fixture.
    """
    _, usage = _point_state(api, monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as raised:
        _ = api.cmd_usage('evil')
    assert raised.value.code == 1
    assert not usage.exists()
    assert 'unknown usage' in capsys.readouterr().err


def test_image_requires_eula_fails_on_an_unreadable_recipe(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing or malformed recipe is a hard error.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
        capsys: Pytest capture fixture.
    """
    monkeypatch.setattr(api, 'RECIPE_FILE', tmp_path / 'missing.json')
    with pytest.raises(SystemExit) as raised:
        _ = api.image_requires_eula('x')
    assert raised.value.code == 1
    assert 'installer recipe unreadable' in capsys.readouterr().err
    _write_recipe(api, monkeypatch, tmp_path, '{')
    with pytest.raises(SystemExit):
        _ = api.image_requires_eula('x')


def test_image_requires_eula_ignores_a_non_object_recipe(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A recipe that is not an object never demands the license.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    _write_recipe(api, monkeypatch, tmp_path, '[]')
    assert api.image_requires_eula('x') is False


def test_image_requires_eula_ignores_a_non_list_images_field(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An images field that is not a list never demands the license.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    _write_recipe(api, monkeypatch, tmp_path, '{"images": {}}')
    assert api.image_requires_eula('x') is False


def test_image_requires_eula_inspects_the_entries(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Only a matching entry carrying a truthy eula demands the license.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    cases: list[tuple[str, str, bool]] = [
        ('{"images": [{"imgref": "x", "eula": "nvidia"}]}', 'x', True),
        ('{"images": [{"imgref": "x", "eula": ""}]}', 'x', False),
        ('{"images": [{"imgref": "y", "eula": "nvidia"}]}', 'x', False),
        ('{"images": ["bad", {"imgref": "x", "eula": 0}]}', 'x', False),
    ]
    for content, imgref, expected in cases:
        _write_recipe(api, monkeypatch, tmp_path, content)
        assert api.image_requires_eula(imgref) is expected


def test_cmd_image_gates_on_the_recorded_flag(
    api: _Api, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A licensed image fails until the flag exists, then passes.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    accepted, _ = _point_state(api, monkeypatch, tmp_path)

    monkeypatch.setattr(api, 'image_requires_eula', _needs_license)
    with pytest.raises(SystemExit) as raised:
        _ = api.cmd_image('x')
    assert raised.value.code == 1
    accepted.parent.mkdir(parents=True)
    _ = accepted.write_text('ok', encoding='utf-8')
    assert api.cmd_image('x') == 0
    monkeypatch.setattr(api, 'image_requires_eula', _open_image)
    assert api.cmd_image('y') == 0


def test_main_without_arguments_fails(
    api: _Api, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty command line prints the usage and exits 1.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capture fixture.
    """
    monkeypatch.setattr(sys, 'argv', ['nvidia-eula-stage'])
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 1
    assert 'nvidia-eula-stage' in capsys.readouterr().err


def test_main_dispatches_probe(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe command exits with the probe status.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(api, 'probe', lambda: 7)
    monkeypatch.setattr(sys, 'argv', ['nvidia-eula-stage', 'probe'])
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 7


def test_main_dispatches_text(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The text command exits with the text status.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(api, 'cmd_text', lambda: 5)
    monkeypatch.setattr(sys, 'argv', ['nvidia-eula-stage', 'text'])
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 5


def test_main_dispatches_consent_with_the_flag(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The consent command forwards the --accept flag.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(api, 'cmd_consent', _consent_status)
    monkeypatch.setattr(
        sys, 'argv', ['nvidia-eula-stage', 'consent', '--accept']
    )
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 3


def test_main_dispatches_usage(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The usage command forwards the profile and its status.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(api, 'cmd_usage', _usage_status)
    monkeypatch.setattr(sys, 'argv', ['nvidia-eula-stage', 'usage', 'ia'])
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 4


def test_main_dispatches_image(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The image command forwards the reference and its status.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(api, 'cmd_image', _image_status)
    monkeypatch.setattr(
        sys, 'argv', ['nvidia-eula-stage', 'image', 'reg/x:latest_amd64']
    )
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 6


@pytest.mark.parametrize(
    'argv', [
        ['bogus'],
        ['usage'],
        ['usage', 'a', 'b'],
        ['image'],
        ['image', 'a', 'b'],
    ]
)
def test_main_rejects_bad_command_lines(
    api: _Api, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """An unknown command or a wrong argument count exits 1 with usage.

    Args:
        api: Loaded helper module.
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capture fixture.
        argv: The command line under test.
    """
    monkeypatch.setattr(sys, 'argv', ['nvidia-eula-stage', *argv])
    with pytest.raises(SystemExit) as raised:
        api.main()
    assert raised.value.code == 1
    assert 'usage:' in capsys.readouterr().err


def test_script_runs_as_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The entry point guard runs main when executed as a script.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Scratch directory.
    """
    state = tmp_path / 'state'
    monkeypatch.setenv('NVIDIA_EULA_STATE_DIR', str(state))
    monkeypatch.setattr(sys, 'argv', ['nvidia-eula-stage', 'usage', 'ia'])
    with pytest.raises(SystemExit) as raised:
        _ = runpy.run_path(str(SCRIPT), run_name='__main__')
    assert raised.value.code == 0
    assert (state / 'gpu-usage').read_text(encoding='utf-8') == 'ia\n'
