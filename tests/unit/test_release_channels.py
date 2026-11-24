"""Tests of the git-flow wiring of the thin caller workflows.

``develop`` is the edge channel and ``main`` the stable one; a workflow cannot
be run outside GitHub, so the triggers are checked on their text.
"""

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / '.github' / 'workflows'


def text(name: str) -> str:
    """Return the text of one caller workflow.

    Args:
        name: File name under ``.github/workflows``.

    Returns:
        The file content.
    """
    return (WORKFLOWS / name).read_text(encoding='utf-8')


def job(name: str, job_name: str) -> str:
    """Return the text of one job of a caller workflow.

    Args:
        name: File name under ``.github/workflows``.
        job_name: Job key.

    Returns:
        The job block, up to the next job or the end of the file.
    """
    found = re.search(
        rf'^  {job_name}:\n(.*?)(?=^  \w+:\n|\Z)', text(name), re.S | re.M
    )
    assert found, f'job {job_name} not found in {name}'
    return found.group(1)


def test_pipeline_and_lint_run_on_both_branches() -> None:
    """A push to develop (edge) or main (stable) runs both workflows."""
    for name in ('pipeline.yml', 'lint.yml'):
        assert 'branches: [main, develop]' in text(name), name


def test_release_follows_both_branches() -> None:
    """The release workflow reacts to a finished run of either branch."""
    assert 'branches: [main, develop]' in text('release.yml')


def test_edge_is_cut_for_develop_only() -> None:
    """Only a green develop run makes an edge pre-release."""
    block = job('release.yml', 'edge')
    assert "head_branch == 'develop'" in block
    assert "conclusion == 'success'" in block


def test_stable_is_cut_for_main_only() -> None:
    """Only a green main run, or a manual run, makes a stable release."""
    block = job('release.yml', 'stable')
    assert "head_branch == 'main'" in block
    assert "conclusion == 'success'" in block
    assert 'workflow_dispatch' in block
