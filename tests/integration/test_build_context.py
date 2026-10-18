"""Static integration checks of the image build context.

``podman build`` is not available everywhere, so these tests verify the inputs
the build consumes: every local ``COPY`` source exists, ``packages.yml`` is
coherent (unique names, resolvable deps and sources) and ``gen-recipe.py``
runs end to end against the real Containerfiles.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / 'workflows' / 'bootc-debs-builder'
CONTAINERFILES = sorted(ROOT.glob('Containerfile*'))
COPY_RE = re.compile(r'^(?:COPY|ADD)\s+(?!--from)(?:--\S+\s+)*(\S+)\s+\S+',
                     re.MULTILINE)


def _local_sources(containerfile: Path) -> list[str]:
  return [
      m for m in COPY_RE.findall(containerfile.read_text())
      if not m.startswith(('http://', 'https://'))
  ]


def _packages() -> list[dict[str, Any]]:
  data = yaml.safe_load((PACKAGES / 'packages.yml').read_text())
  return cast(list[dict[str, Any]], data['packages'])


def test_containerfiles_found() -> None:
  """The glob finds the three image definitions."""
  assert len(CONTAINERFILES) >= 3


@pytest.mark.parametrize('containerfile', CONTAINERFILES, ids=lambda p: p.name)
def test_copy_sources_exist(containerfile: Path) -> None:
  """Every local COPY/ADD source resolves in the build context."""
  for source in _local_sources(containerfile):
    pattern = source.removeprefix('./')
    assert list(ROOT.glob(pattern)), f'{containerfile.name}: {source} missing'


def test_package_names_unique() -> None:
  """Package names are unique and non-empty."""
  names = [p['name'] for p in _packages()]
  assert all(names)
  assert len(names) == len(set(names))


def test_package_deps_resolve() -> None:
  """Every dependency names another package of the manifest."""
  packages = _packages()
  names = {p['name'] for p in packages}
  for pkg in packages:
    for dep in pkg.get('deps') or []:
      assert dep in names, f"{pkg['name']} depends on unknown {dep}"


def test_package_sources_exist() -> None:
  """Every hashed source path exists under the builder directory."""
  for pkg in _packages():
    for source in pkg.get('sources') or []:
      assert (PACKAGES / source).exists(), f"{pkg['name']}: {source} missing"


def test_package_has_build_or_upstream() -> None:
  """Each package either repacks an upstream deb or carries a build script."""
  for pkg in _packages():
    assert pkg.get('upstream') or str(pkg.get('build', '')).strip(), pkg['name']


def test_gen_recipe_runs_on_real_containerfiles(tmp_path: Path) -> None:
  """gen-recipe.py updates a recipe from the repo's Containerfiles."""
  recipe = tmp_path / 'recipe.json'
  recipe.write_text(json.dumps({'distro_name': 'debian bootc', 'keep': 1}))
  subprocess.run(
      [sys.executable, '-I',
       str(ROOT / 'scripts' / 'gen-recipe.py'),
       str(ROOT),
       str(recipe)],
      check=True,
      capture_output=True,
      env={'IMAGE_REGISTRY': 'ghcr.io/example/repo'},
  )
  result = json.loads(recipe.read_text())
  assert result['keep'] == 1
  assert result['images']
