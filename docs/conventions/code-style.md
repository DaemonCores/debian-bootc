# Code and comment conventions

Adopted for KT-2 [src: user:pikatsuto:2026-10-18: disc-dc54c008]. Rule: follow the Google style guides; the tools in `make check` enforce what can be enforced mechanically [src: file: Makefile:1].

| Language | Guide | Enforced by |
|----------|-------|-------------|
| Python | [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) — Google docstrings (`Args:`, `Returns:`), 80 columns, type hints | ruff (pydocstyle `google`), yapf, docformatter, pydoclint, mypy, basedpyright, bandit [src: file: pyproject.toml:1] |
| Shell | [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) — 2-space indent, operators on the continuation line, indented `case`, file header comment | shellcheck, `shfmt -i 2 -bn -ci` (`SHFMT_FLAGS`), [.editorconfig](../../.editorconfig) [src: file: Makefile:1] |
| Containerfile | hadolint defaults + [coding-rules](../coding-rules.md) | hadolint, `.hadolint.yaml` |
| YAML | yamllint defaults + [coding-rules](../coding-rules.md) | yamllint, `.yamllint.yml` |

## Comments that generate documentation

- **Python:** every module, function and class carries a Google-style docstring. `make docs` renders them into `docs/reference/Reference-Python.md`.
- **Shell:** every script starts, right after the shebang, with a comment block `name - one-line purpose`, followed by details. `make docs` renders them into `docs/reference/Reference-Shell.md`.
- Generated pages sit between `<!-- gen:reference start/end -->` markers; never edit between them. CI runs `make docs-check` and fails when the committed pages are stale [src: file: .github/workflows/lint.yml:1].

## Deviations from the reference (cunegonde-ai `agentic-backend`)

- Generation uses `ast` + a header-comment scan (`scripts/gen_docs.py`) instead of `pydoc-markdown`: the script file names contain hyphens, which `pydoc-markdown` cannot import as modules. Hypothesis, not tested against `pydoc-markdown`.
- The Google `pylintrc` named in KT-1 is not used: the reference config (ruff + mypy + basedpyright) wins, as recorded in [quality-targets](quality-targets.md).
- `style.py` and the reference pre-commit hook stay out: they depend on cunegonde-ai internals.
