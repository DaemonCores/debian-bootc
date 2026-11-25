"""Contract between the installer pkexec calls and the live image helpers.

The installer GPU step runs its helpers with ``pkexec`` as the ``live`` user in
an agent-less session. A helper that is not executable (git mode 100644) exits
127 ("Permission denied"), and a helper without a polkit rule needs an
authentication nobody can give: both made the step fail with "The choice could
not be recorded" on the published ISO.
"""

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBEXEC = (
    ROOT / 'src' / 'buildisopreinstall' / 'usr' / 'libexec' / 'debian-bootc'
)
RULES = (
    ROOT / 'src' / 'buildisopreinstall' / 'etc' / 'polkit-1' / 'rules.d' /
    '50-bootc-installer-live.rules'
)
GPU_CONFIG = (
    ROOT / 'workflows' / 'bootc-debs-builder' / 'bootc_installer' / 'utils' /
    'gpu_config.py'
)
HELPER_CONSTANT = re.compile(r'^[A-Z_]*HELPER\s*=\s*"([^"]+)"', re.MULTILINE)
LIBEXEC_PREFIX = '/usr/libexec/debian-bootc/'


def pkexec_helpers() -> list[str]:
    """List the helper paths the installer GPU step passes to pkexec.

    Returns:
        The absolute helper paths declared in ``gpu_config.py``.
    """
    return HELPER_CONSTANT.findall(GPU_CONFIG.read_text())


def test_gpu_config_declares_helpers() -> None:
    """Both helpers must be found, else the other tests are void."""
    assert len(pkexec_helpers()) >= 2


@pytest.mark.parametrize('helper', pkexec_helpers())
def test_helper_is_in_the_live_image_and_executable(helper: str) -> None:
    """The file must ship with the execute bit, pkexec needs it.

    Args:
        helper: Absolute helper path declared by the installer.
    """
    assert helper.startswith(LIBEXEC_PREFIX)
    path = LIBEXEC / helper.removeprefix(LIBEXEC_PREFIX)
    assert path.is_file(), f'{helper} is not shipped in the live image'
    assert os.access(
        path, os.X_OK
    ), f'{path} is not executable (exit 127 under pkexec)'


@pytest.mark.parametrize('helper', pkexec_helpers())
def test_helper_has_a_polkit_rule_for_live(helper: str) -> None:
    """Without a rule, pkexec asks for a password nobody can type.

    Args:
        helper: Absolute helper path declared by the installer.
    """
    rules = RULES.read_text()
    assert f'"{helper}"' in rules, f'no polkit rule allows {helper} for live'
