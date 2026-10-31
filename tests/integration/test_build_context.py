"""Repository-specific checks of the image build context.

The generic checks (COPY sources, ``.dockerignore`` exclusions, package manifest
coherence) are shared by every repository and live in ``DaemonCores-
CI/scripts/check_build_context.py``, run by ``make check``. What stays here
concerns this repository only: ``gen-recipe.py`` against the real
Containerfiles, the local-state exclusions and the kernel helper users.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / 'workflows' / 'bootc-debs-builder'


def _packages() -> list[dict[str, Any]]:
    """Load the package entries of ``packages.yml``.

    Returns:
        One mapping per package of the manifest.
    """
    data = yaml.safe_load((PACKAGES / 'packages.yml').read_text())
    return cast(list[dict[str, Any]], data['packages'])


def test_gen_recipe_runs_on_real_containerfiles(tmp_path: Path) -> None:
    """gen-recipe.py updates a recipe from the repo's Containerfiles.

    Args:
        tmp_path: Scratch directory holding the recipe file.
    """
    recipe = tmp_path / 'recipe.json'
    recipe.write_text(json.dumps({'distro_name': 'debian bootc', 'keep': 1}))
    subprocess.run(
        [
            sys.executable, '-I',
            str(
                ROOT / 'src' / 'buildisopreinstall' / 'usr' / 'libexec' /
                'debian-bootc' / 'gen-recipe.py'
            ),
            str(ROOT),
            str(recipe)
        ],
        check=True,
        capture_output=True,
        env={'IMAGE_REGISTRY': 'ghcr.io/example/repo'},
    )
    result = json.loads(recipe.read_text())
    assert result['keep'] == 1
    assert result['images']


def test_dockerignore_excludes_local_state() -> None:
    """Agent state, MCP config and env files stay out of the build context."""
    lines = (ROOT / '.dockerignore').read_text().splitlines()
    patterns = {ln.strip() for ln in lines if ln.strip()}
    for required in ('.env*', '.kronn/', '.claude/', '.mcp.json*', 'docs/'):
        assert required in patterns, f'{required} missing from .dockerignore'


def test_kernel_prepare_users() -> None:
    """The module entries bootstrap through the shared kernel_prepare."""
    users = {
        entry['name']
        for entry in _packages()
        if 'kernel_prepare' in str(entry.get('build', ''))
    }
    assert users == {'linux-modules-arm-device', 'linux-modules-nvidia'}


def test_kernel_signing_users() -> None:
    """The kernel and the module entries sign with the same key helper."""
    users = {
        entry['name']
        for entry in _packages()
        if 'kernel_signing_setup' in str(entry.get('build', ''))
    }
    assert users == {
        'linux-image', 'linux-modules-arm-device', 'linux-modules-nvidia'
    }


def test_kernel_image_verifies_signing() -> None:
    """The kernel entry checks the signing options after olddefconfig."""
    kernel = next(e for e in _packages() if e['name'] == 'linux-image')
    assert 'kernel_signing_verify' in kernel['build']
