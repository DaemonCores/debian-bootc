"""Unit tests for the repository module loader."""

import importlib.util
from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest

from tests.support.modules import load_module

SOURCE = "def answer() -> int:\n    return 42\n"


@runtime_checkable
class _Sample(Protocol):
    """Surface of the sample module built by the tests."""

    def answer(self) -> int:
        """Return the sample answer.

        Returns:
            The constant answer.
        """
        ...


def test_load_module_executes_the_source(tmp_path: Path) -> None:
    """The loader runs the file with real module semantics.

    Args:
        tmp_path: Scratch directory holding the source file.
    """
    target = tmp_path / 'sample.py'
    _ = target.write_text(SOURCE, encoding='utf-8')
    module = load_module('sample', target)
    assert isinstance(module, _Sample)
    assert module.answer() == 42


def test_load_module_reports_an_unbuildable_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A loader without a spec is reported instead of crashing later.

    Args:
        tmp_path: Scratch directory holding the source file.
        monkeypatch: Pytest monkeypatch fixture.
    """
    target = tmp_path / 'sample.py'
    _ = target.write_text(SOURCE, encoding='utf-8')

    def no_spec(name: str, loader: object) -> None:
        """Return no spec, whatever the loader.

        Args:
            name: Module name (unused).
            loader: Loader instance (unused).
        """
        _ = (name, loader)

    monkeypatch.setattr(importlib.util, 'spec_from_loader', no_spec)
    with pytest.raises(ImportError, match='cannot load'):
        _ = load_module('sample', target)
