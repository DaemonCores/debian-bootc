"""Unit tests for the helpers of ``firstboot-user-setup``.

The script grabs /dev/tty1 on start, so it cannot run whole.  The tests cut
the helper functions out of the source and run them in a plain bash with stub
``_pass`` and ``_msg`` functions.
"""

import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'firstbootpostinstall' / 'usr' / 'local' / 'bin' / 'firstboot-user-setup'
)


def _function(name: str) -> str:
    """Cut one top-level shell function out of the script.

    Args:
        name: Name of the shell function to extract.

    Returns:
        The source of the function, from its name to the closing brace.
    """
    match = re.search(
        rf'^{name}\(\) \{{\n.*?^\}}\n', SCRIPT.read_text(),
        re.MULTILINE | re.DOTALL
    )
    assert match, f'{name} not found'
    return match.group(0)


def _bash(snippet: str) -> subprocess.CompletedProcess[str]:
    """Run a snippet in a strict bash.

    Args:
        snippet: Shell source to execute.

    Returns:
        The completed process, with captured text output.
    """
    return subprocess.run(['bash', '-euo', 'pipefail', '-c', snippet],
                          check=False,
                          capture_output=True,
                          text=True,
                          timeout=10)


@pytest.mark.parametrize(('hostname', 'expected'), [
    ('my-system', 'My System'),
    ('my_system', 'My System'),
    ('host.local', 'Host'),
    ('a--b', 'A B'),
])
def test_display_name(hostname: str, expected: str) -> None:
    """Hostnames become title-case names; - and _ are spaces, domain dropped.

    Args:
        hostname: Hostname given to the helper.
        expected: Display name the helper must produce.
    """
    result = _bash(f'{_function("_display_name")}\n_display_name {hostname!r}')
    assert result.stdout.strip() == expected


def test_ask_password_retries_until_valid() -> None:
    """Short and mismatching entries are rejected, a valid pair is returned."""
    snippet = f"""
{_function('_ask_password')}
answers=(short longenough1 longenough2 goodpassword goodpassword)
counter=$(mktemp); echo 0 >"$counter"
_pass() {{ # runs in a subshell, so the position lives in a file
  local n; n=$(<"$counter"); echo $((n + 1)) >"$counter"
  printf '%s' "${{answers[n]}}"
}}
_msg() {{ echo "MSG: $1" >&2; }}
_ask_password SECRET 'first' 'confirm'
echo "result=$SECRET"
"""
    result = _bash(snippet)
    assert result.stdout.strip() == 'result=goodpassword'
    assert result.stderr.count('at least 8 characters') == 1
    assert result.stderr.count('do not match') == 1
