# Quality targets (declared, not yet implemented)

Target state declared by the maintainer on 2026-10-18 [src: user:pikatsuto:2026-10-18: disc-dc54c008]. It applies to **every language in the repo**: Containerfile, bash/sh, Python, YAML and any other. The current state is in [coding-rules](../coding-rules.md) and [testing-quality](../testing-quality.md). Until the work lands, do not describe these targets as already in place.

## Why

The goal is faster development and debugging. CI has been broken since arm64 support work started, and arm64 is not functional yet [src: user:pikatsuto:2026-10-18: disc-dc54c008] [src: file: README.md:20].

## Targets

| Area | Target | Current state |
|------|--------|---------------|
| Linter, formatter, type-checker | One of each per language, configured in versioned config files. Their absence is a problem to fix | **KT-1 done:** shellcheck + shfmt (shell), hadolint (Containerfile), yamllint (YAML), ruff (Python) — configs at `.shellcheckrc`, `.hadolint.yaml`, `.yamllint.yml`, `pyproject.toml` [src: file: Makefile:1]. Type-checkers mypy + basedpyright: done (KT-2). |
| Code and comment conventions | Mostly follow the Google style guides. Write structured comments so CI/CD can generate technical and API documentation | **KT-2 done:** Google styles adopted, see [code-style](code-style.md); `make docs` generates `docs/reference/`, `make docs-check` runs in CI |
| Tests | Unit, integration and end-to-end | Only build-time content checks, one `cargo test`, and QEMU runtime tests [src: file: docs/testing-quality.md:10-17] |
| Local execution | Every test that can run locally must be runnable locally, not only in CI | **KT-1 done:** `make test` runs local smoke checks (manifest integrity, Python syntax, ruff); `make lint` runs all linters locally [src: file: Makefile:1]. Runtime QEMU tests remain CI-only. |

## Chosen tooling (KT-1)

Decided by the maintainer on 2026-10-18 [src: user:pikatsuto:2026-10-18: disc-dc54c008 quality-targets-lint-tools].

| Language | Linter | Formatter | Type checker |
|----------|--------|-----------|--------------|
| Shell (bash/sh) | shellcheck | shfmt | N/A |
| Containerfile | hadolint | N/A | N/A |
| YAML | yamllint | N/A | N/A |
| Python | Google's linter: pylint with the `pylintrc` from the Google Python Style Guide [src: url: https://google.github.io/styleguide/pyguide.html] | Not chosen yet; pick it during KT-1 | pyright |

- **Entry point:** a root `Makefile` is the single entry point for **every** project action (lint, format, test, build, docs). Local runs and CI call the same targets [src: user:pikatsuto:2026-10-18: disc-dc54c008 quality-targets-lint-tools].
- **pre-commit:** optional; it may call the `Makefile` targets, never duplicate their logic [src: user:pikatsuto:2026-10-18: disc-dc54c008 quality-targets-lint-tools].

## Reference configuration: cunegonde-ai `agentic-backend`

The maintainer's `cunegonde-ai/agentic-backend` repository is the reference for lint and documentation generation. Copy its lint config (including its custom rules) and its doc-generation config **as is** into this project [src: user:pikatsuto:2026-10-18: disc-dc54c008 quality-targets-docgen]. Where its lint config differs from the tool table above, the reference config wins. Its organisation of handoff `.md` files is also a candidate model for this repo [src: user:pikatsuto:2026-10-18: disc-dc54c008 quality-targets-docgen].

**KT-1 audit of the reference (2026-10-18):** tools found and copied/not-copied:

| Item | Copied | Note |
|------|--------|------|
| `pyproject.toml` — ruff, yapf, docformatter, pydoclint, mypy, basedpyright sections | ✓ copied as-is into this repo; only `target-version` (py311), `mypy_path`, `basedpyright.extraPaths` and `basedpyright.pythonVersion` adapted for the single-file scripts/ surface | |
| `setup.cfg` admission extras (ruff, yapf, docformatter, mypy, basedpyright, pydoclint, bandit versions) | ✓ pinned in `Makefile` `admission` target; not a Python package so no setup.cfg | |
| `scripts/style.py` — custom readability gate | ✗ not portable: imports from `tests.enforcement.*` (a cunegonde-ai internal package); equivalent rules for debian-bootc not adopted: a project-specific gate is out of scope for KT-2 | |
| `gen_docs.py` — API/docstring reference generation | ✗ not portable: tightly coupled to the cunegonde-ai Python package structure; replaced by the shared `DaemonCores-CI/scripts/gen_docs.py` (see [code-style](code-style.md)) | |
| `hooks/pre-commit` | ✗ not applicable: tied to cunegonde-ai's doc-submodule, facet architecture and frontend; debian-bootc pre-commit (optional) not added | |

## Languages without a Google style guide

Decided by the maintainer on 2026-10-18 [src: user:pikatsuto:2026-10-18: disc-dc54c008 quality-targets-non-google-langs]:

- **Containerfile:** hadolint default rules, plus the existing conventions in [coding-rules](../coding-rules.md).
- **YAML:** yamllint default rules, plus the existing conventions in [coding-rules](../coding-rules.md).
- **Shell inside `RUN` instructions:** follows the Google Shell Style Guide like any other shell code [src: url: https://google.github.io/styleguide/shellguide.html].
- If the reference config above sets rules for these languages, it wins over the defaults (same rule as for the tool table) [src: inferred: follows from the "copy as is" instruction above].

## Deferred: ublue conformance

After the code is proven and stable, a large refactor will align the project with ublue. Its goal is to get official Debian support into bootc and ublue, which upstream has requested since 2024 [src: user:pikatsuto:2026-10-18: disc-dc54c008]. Do not start it before the targets above are met.

Plan tasks: KT-1 (tooling — **done 2026-10-18**), KT-2 (conventions + doc generation — **done 2026-10-18**), KT-3 (tests), KT-4 (deferred ublue refactor).
