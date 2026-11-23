"""Load repository Python sources as modules."""

import importlib.machinery
import importlib.util
from pathlib import Path
from types import ModuleType


def load_module(name: str, path: Path) -> ModuleType:
    """Execute one Python source file as a module.

    The repository stages are extensionless files ("org.osbuild.dracut"),
    so the loader is chosen explicitly instead of being guessed from a
    suffix; "exec_module" runs the file with real module semantics, unlike
    "exec".

    Args:
        name: Module name used for tracebacks and metadata.
        path: Python source file.

    Returns:
        The executed module object.

    Raises:
        ImportError: when no loader can be built for the file.
    """
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ImportError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module
