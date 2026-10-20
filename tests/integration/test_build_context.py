"""Repository-specific checks of the image build context.

The generic checks (COPY sources, ``.dockerignore`` exclusions, package
manifest coherence) are shared by every repository and live in
``DaemonCores-CI/scripts/check_build_context.py``, run by ``make check``.
What stays here concerns this repository only: ``gen-recipe.py`` against the
real Containerfiles, the local-state exclusions and the kernel helper users.
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
            str(ROOT / 'scripts' / 'gen-recipe.py'),
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


def test_kernel_prepare_users_hash_the_library() -> None:
    """Every entry sourcing kernel-prepare.sh lists it in its sources."""
    library = 'lib/kernel-prepare.sh'
    assert (PACKAGES / library).is_file()
    users = [
        entry for entry in _packages()
        if 'kernel_prepare' in str(entry.get('build', ''))
    ]
    assert {e['name'] for e in users} == {'linux-modules-arm-device'}
    for entry in users:
        assert library in entry['sources'], entry['name']
        assert 'lib/kernel-prepare.sh' in entry['build']


def test_kernel_signing_users_hash_the_library() -> None:
    """The kernel and the module entries sign with the same key helper."""
    library = 'lib/kernel-signing.sh'
    assert (PACKAGES / library).is_file()
    users = [
        entry for entry in _packages()
        if 'kernel_signing_setup' in str(entry.get('build', ''))
    ]
    assert {e['name']
            for e in users} == {'linux-image', 'linux-modules-arm-device'}
    for entry in users:
        assert library in entry['sources'], entry['name']


def test_kernel_signing_forces_only_when_active() -> None:
    """Enforcement and the MOK keyrings are tied to the signing option."""
    text = (PACKAGES / 'lib/kernel-signing.sh').read_text()
    assert 'MODULE_SIG_FORCE' in text
    assert 'INTEGRITY_MACHINE_KEYRING' in text
    assert 'kernel_signing_verify' in text
    kernel = next(e for e in _packages() if e['name'] == 'linux-image')
    assert 'kernel_signing_verify' in kernel['build']


def test_apt_source_placeholders_are_all_substituted() -> None:
    """Both Containerfiles fill every token of the APT source, suite included.

    The unsigned image of the ``both`` signing mode differs from the signed one
    only by the suite and component it receives as build arguments.
    """
    source = (
        ROOT / 'src' / 'bootcpreinstall' / 'etc' / 'apt' / 'sources.list.d' /
        'debian-bootc.sources'
    ).read_text()
    tokens = {'ARCH', 'APT_URL', 'APT_SUITE', 'APT_COMPONENT'}
    assert {t for t in tokens if '{{ ' + t + ' }}' in source} == tokens
    for name in ('Containerfile', 'Containerfile.minimal'):
        text = (ROOT / name).read_text()
        for token in tokens:
            assert '{{ ' + token + ' }}' in text, f'{name}: {token}'
        assert 'ARG BOOTC_APT_SUITE=trixie\n' in text
        assert 'ARG BOOTC_APT_COMPONENT=main\n' in text
