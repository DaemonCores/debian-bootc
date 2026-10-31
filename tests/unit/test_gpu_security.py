"""GPU / module-signature step of the installer."""

import json
import subprocess
import types
from pathlib import Path
from typing import Any

BUILDER = Path(__file__
               ).resolve().parents[2] / 'workflows' / 'bootc-debs-builder'
INSTALLER = BUILDER / 'bootc-installer-src'
FISHERMAN = BUILDER / 'fisherman-src'
RECIPE = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'etc' /
    'bootc-installer' / 'recipe.json'
)


def _overlay_text(overlay: Path) -> str:
    """Return the concatenated text of one source overlay.

    Args:
        overlay: Overlay directory.

    Returns:
        Every patch and added file of the overlay, joined.
    """
    return '\n'.join(
        f.read_text() for f in sorted(overlay.rglob('*'))
        if f.is_file() and '__pycache__' not in f.parts
    )


def _module() -> types.ModuleType:
    """Load ``gpu_config.py`` straight from the installer overlay.

    Returns:
        The module, executed without any GTK dependency.
    """
    module = types.ModuleType('gpu_config')
    exec(
        compile((INSTALLER / 'bootc_installer' / 'utils' /
                 'gpu_config.py').read_text(), 'gpu_config.py', 'exec'),
        module.__dict__
    )
    return module


class _Runner:
    """Record the commands and answer with a scripted exit status."""

    def __init__(self, fail_on: str = '') -> None:
        """Start with no recorded command.

        Args:
            fail_on: Command word that makes the call exit with status 1.
        """
        self.commands: list[list[str]] = []
        self.fail_on = fail_on

    def __call__(
        self, command: list[str], **kwargs: object
    ) -> 'subprocess.CompletedProcess[str]':
        """Record the command and return the scripted result.

        Args:
            command: Command line.
            **kwargs: Ignored ``subprocess.run`` keywords.

        Returns:
            A completed process with the scripted status.
        """
        self.commands.append(command)
        failed = bool(self.fail_on) and self.fail_on in command
        return subprocess.CompletedProcess(
            command, 1 if failed else 0, 'out', ''
        )


CATALOG = {
    'imgref':
    'reg/x:latest_amd64',
    'images': [
        {
            'imgref': 'reg/x:latest_amd64'
        },
        {
            'imgref': 'reg/x:nvidia_amd64',
            'eula': 'nvidia'
        },
    ],
}


def test_eula_follows_the_selected_image() -> None:
    """Only the catalog entry carrying ``eula`` asks for the license."""
    m = _module()
    assert m.eula_required(CATALOG, 'reg/x:nvidia_amd64')
    for imgref in ('reg/x:latest_amd64', 'custom/y:1', ''):
        assert not m.eula_required(CATALOG, imgref), imgref
    assert not m.eula_required(None, 'reg/x:nvidia_amd64')


def test_selected_imgref_priority() -> None:
    """Custom image, then catalog selection, then the recipe default."""
    m = _module()
    both = {'custom_image': 'c', 'selected_image': 's'}
    assert m.selected_imgref(both, CATALOG) == 'c'
    assert m.selected_imgref({'selected_image': 's'}, CATALOG) == 's'
    assert m.selected_imgref({}, CATALOG) == 'reg/x:latest_amd64'
    assert m.selected_imgref(None, None) == ''


def test_acceptance_is_the_exact_word() -> None:
    """Anything but ACCEPT is a refusal."""
    m = _module()
    assert m.eula_accepted('ACCEPT')
    for typed in ('', 'accept', 'ACCEPT ', 'yes'):
        assert not m.eula_accepted(typed), typed


def test_stage_choice_goes_through_the_helper() -> None:
    """Consent first (when accepted), then the usage, both via pkexec."""
    m = _module()
    run = _Runner()
    assert m.stage_choice('ia', True, 'reg/x:nvidia_amd64', run)
    assert run.commands == [
        ['pkexec', m.HELPER, 'consent', '--accept'],
        ['pkexec', m.HELPER, 'usage', 'ia'],
        ['pkexec', m.HELPER, 'image', 'reg/x:nvidia_amd64'],
    ]
    run = _Runner()
    assert m.stage_choice('gaming', False, run=run)
    assert run.commands == [['pkexec', m.HELPER, 'usage', 'gaming']]


def test_image_gate_refusal_is_reported() -> None:
    """The helper refusing the image fails the step."""
    m = _module()
    run = _Runner(fail_on='image')
    assert not m.stage_choice('ia', False, 'reg/x:nvidia_amd64', run)


def test_stage_choice_refusals_are_reported() -> None:
    """The helper refusing the profile, or an unknown profile, is a failure."""
    m = _module()
    assert not m.stage_choice('ia', False, run=_Runner(fail_on='usage'))
    run = _Runner()
    assert not m.stage_choice('evil', True, run=run)
    assert run.commands == []


def test_apply_gpu_fills_the_recipe() -> None:
    """Usage, consent and enforcement reach the recipe."""
    m = _module()
    recipe: dict[str, Any] = {}
    m.apply_gpu(
        recipe, {
            'usage': 'ia',
            'nvidiaConsent': True,
            'sigEnforce': True
        }
    )
    assert recipe == {
        'gpuUsage': 'ia',
        'nvidiaConsent': True,
        'sigEnforce': True
    }


def test_apply_gpu_disabled_enforcement_is_written() -> None:
    """Turning enforcement off is an explicit False, not an absence."""
    m = _module()
    recipe: dict[str, Any] = {}
    m.apply_gpu(recipe, {'usage': 'auto', 'sigEnforce': False})
    assert recipe['sigEnforce'] is False
    assert recipe['nvidiaConsent'] is False


def test_apply_gpu_without_step_changes_nothing() -> None:
    """A skipped step and an unknown usage leave the recipe untouched."""
    m = _module()
    recipe: dict[str, Any] = {}
    m.apply_gpu(recipe, None)
    m.apply_gpu(recipe, {'usage': 'evil'})
    assert recipe == {}


def test_step_is_in_the_recipe() -> None:
    """The ISO recipe offers the step before the user one."""
    steps = json.loads(RECIPE.read_text())['steps']
    keys = list(steps)
    assert steps['gpu_security'] == {'template': 'gpu_security'}
    assert keys.index('gpu_security') < keys.index('user')


def test_step_is_registered_in_the_installer() -> None:
    """Template, UI resource, build lists and recipe merge are all wired."""
    installer = _overlay_text(INSTALLER)
    assert '"gpu_security": BootcDefaultGpuSecurity' in installer
    assert 'gtk/default-gpu-security.ui' in installer
    assert "gtk/default-gpu-security.blp" in installer
    assert "'gpu_security.py'" in installer
    assert "'gpu_config.py'" in installer
    assert 'apply_gpu(recipe, merged.get("gpu"))' in installer
    assert (INSTALLER / 'bootc_installer' / 'gtk' /
            'default-gpu-security.blp').is_file()


def test_installer_fields_match_the_fisherman_recipe() -> None:
    """The recipe keys written by the installer are read by fisherman."""
    installer = _overlay_text(INSTALLER)
    fisherman = _overlay_text(FISHERMAN)
    for key in ('gpuUsage', 'nvidiaConsent', 'sigEnforce'):
        assert f'recipe["{key}"]' in installer, key
        assert f'json:"{key},omitempty"' in fisherman, key
    assert 'post.WriteGPUProfile(' in fisherman
    call = 'post.EnsureKernelArg(activeTargetMount, post.SigEnforceArg)'
    assert call in fisherman
    assert 'module.sig_enforce=1' in fisherman


def test_files_match_what_dc_gpu_reads() -> None:
    """Fisherman writes the exact files ``dc-gpu`` reads."""
    gpu_go = (FISHERMAN / 'fisherman' / 'internal' / 'post' /
              'gpu.go').read_text()
    dc_gpu = (
        BUILDER.parents[1] / 'src' / 'basepostinstall' / 'usr' / 'sbin' /
        'dc-gpu'
    ).read_text()
    assert '"dc-gpu"' in gpu_go
    assert 'conf=${root}/etc/dc-gpu' in dc_gpu
    for name in ('usage', 'nvidia-consent'):
        assert f'"{name}"' in gpu_go
        assert f'${{conf}}/{name}' in dc_gpu
