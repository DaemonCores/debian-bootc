"""Docstring presence gate for every Python file of the repository.

ruff ignores private callables and pydoclint only checks docstrings that
exist, so neither catches a helper or a test with no docstring at all.  This
gate closes the gap: every module, class and function (private and test ones
included) is documented, and a callable with arguments, a return value or a
raised exception explains them in a Google-style section instead of a lone
summary line.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCES = sorted([
    *(ROOT / 'scripts').glob('*.py'), *(ROOT / 'tests').rglob('*.py')
])
_DEF = (ast.FunctionDef, ast.AsyncFunctionDef)


def _needs_sections(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Name the docstring sections a function must carry.

    Args:
        node: Function definition to inspect.

    Returns:
        The section headers (``Args:``, ``Returns:``, ``Raises:``,
        ``Yields:``) the docstring has to contain.
    """
    signature = node.args
    names = [
        a.arg for a in
        [*signature.posonlyargs, *signature.args, *signature.kwonlyargs]
        if a.arg not in {'self', 'cls'}
    ]
    names += [a.arg for a in (signature.vararg, signature.kwarg) if a]
    body = [n for stmt in node.body for n in ast.walk(stmt)]
    sections = []
    if names:
        sections.append('Args:')
    if any(isinstance(n, ast.Yield) for n in body):
        sections.append('Yields:')
    elif any(isinstance(n, ast.Return) and n.value for n in body):
        sections.append('Returns:')
    if any(isinstance(n, ast.Raise) for n in body):
        sections.append('Raises:')
    return sections


def _problems(path: Path) -> list[str]:
    """Collect the docstring defects of one Python file.

    Args:
        path: Python file to inspect.

    Returns:
        One human-readable line per missing docstring or section.
    """
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = []
    if not ast.get_docstring(tree):
        found.append(f'{path.name}: module docstring missing')
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, *_DEF)):
            continue
        where = f'{path.name}:{node.lineno} {node.name}'
        doc = ast.get_docstring(node)
        if not doc:
            found.append(f'{where}: docstring missing')
        elif isinstance(node, _DEF):
            found.extend(
                f'{where}: {section} section missing'
                for section in _needs_sections(node) if section not in doc
            )
    return found


@pytest.mark.parametrize(
    'path', SOURCES, ids=lambda p: str(p.relative_to(ROOT))
)
def test_every_definition_is_documented(path: Path) -> None:
    """Modules, classes and functions carry complete Google docstrings.

    Args:
        path: Python file under test.
    """
    assert not _problems(path)
