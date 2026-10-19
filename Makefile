# Single entry point for all project actions (KT-1).
# Local runs and CI call the same targets.
# See docs/conventions/quality-targets.md for the full roadmap.
#
# Makefile structure follows cunegonde-ai/agentic-backend (the reference repo).

SHELL := /bin/bash -euo pipefail

# ---- Python venv (tools only — debian-bootc is not a Python package) ------ #

VENV = .venv
VBIN = $(VENV)/bin

# ---- file sets ------------------------------------------------------------ #

SHELL_SRCS := \
	src/buildisopreinstall/sbin/policy-rc.d \
	src/debianpreinstall/usr/sbin/policy-rc.d \
	workflows/bootc-debs-builder/preinstall/usr/sbin/policy-rc.d \
	workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set \
	workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf \
	workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize \
	workflows/bootc-debs-builder/bootcpostinstall/etc/kernel/postinst.d/zz-bootc-finalize \
	workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup \
	workflows/bootc-debs-builder/lib/kernel-prepare.sh \
	scripts/e2e-local.sh

# DEBIAN/postinst files use `set -e` (POSIX sh, not full bash pipefail).
POSTINST_SRCS := \
	workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/postinst \
	workflows/bootc-debs-builder/preinstall/output/ostree/DEBIAN/postinst \
	workflows/bootc-debs-builder/preinstall/output/bootupd/DEBIAN/postinst \
	src/ostreelayout/usr/libexec/debian-bootc/ostree-layout \
	workflows/bootc-debs-builder/preinstall/output/grub-efi-amd64-signed/DEBIAN/postinst

CONTAINERFILES := Containerfile Containerfile.minimal Containerfile.iso

# Google Shell Style: 2 spaces, operators on the continuation line, indented case.
# Explicit flags: shfmt ignores .editorconfig once any flag is given (-ln).
SHFMT_FLAGS := -i 2 -bn -ci

YAML_SRCS := \
	config.yml \
	workflows/bootc-debs-builder/packages.yml \
	workflows/env.yml \
	workflows/tests.yml

PYTHON_SRCS := scripts/check_upstream_pins.py scripts/gen-recipe.py scripts/gen_docs.py
PYTHON_TESTS := tests

# ---- venv bootstrap ------------------------------------------------------- #

$(VBIN)/python:
	@if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then \
		python3 -m venv $(VENV); \
	elif command -v python3.11 >/dev/null 2>&1; then \
		python3.11 -m venv $(VENV); \
	else \
		echo "No Python >= 3.11 found" >&2; exit 1; \
	fi

# Install the admission toolchain (lint, type, security).
# Versions pinned to match cunegonde-ai/agentic-backend setup.cfg [admission].
admission: $(VBIN)/python
	@$(VBIN)/pip install --quiet --upgrade \
		'ruff>=0.16.8' \
		'yapf>=0.43.0' \
		'docformatter>=1.7.8' \
		'mypy>=2.3.1' \
		'basedpyright>=1.40.1' \
		'pydoclint>=0.9.1' \
		'bandit>=1.9.4' \
		'pytest>=8'

# No-op once the toolchain is provisioned (fast path for every py-using target).
py-ready:
	@test -x $(VBIN)/ruff || $(MAKE) admission

# ---- check (verification gate) ------------------------------------------- #
# Mirrors the reference `check-back` target: format-diff, lint, types, security.
# All four sub-checks must pass for the gate to be green.

.PHONY: check check-py check-shell check-containerfile check-yaml

check: check-py check-shell check-containerfile check-yaml

check-py: py-ready
	$(VBIN)/yapf --diff --recursive $(PYTHON_SRCS) $(PYTHON_TESTS)
	$(VBIN)/docformatter --check --diff --recursive $(PYTHON_SRCS)
	$(VBIN)/ruff check $(PYTHON_SRCS) $(PYTHON_TESTS)
	$(VBIN)/mypy --explicit-package-bases $(PYTHON_SRCS)
	$(VBIN)/basedpyright $(PYTHON_SRCS)
	$(VBIN)/pydoclint $(PYTHON_SRCS)
	$(VBIN)/bandit -q -r $(PYTHON_SRCS) --severity-level medium

check-shell:
	@command -v shellcheck >/dev/null 2>&1 || { echo "shellcheck not found — apt install shellcheck" >&2; exit 1; }
	shellcheck $(SHELL_SRCS)
	shellcheck --shell=sh $(POSTINST_SRCS)
	@command -v shfmt >/dev/null 2>&1 || { echo "shfmt not found — apt install shfmt" >&2; exit 1; }
	shfmt -d $(SHFMT_FLAGS) $(SHELL_SRCS)
	shfmt -d $(SHFMT_FLAGS) -ln posix $(POSTINST_SRCS)

check-containerfile:
	@command -v hadolint >/dev/null 2>&1 || { echo "hadolint not found — apt install hadolint" >&2; exit 1; }
	hadolint $(CONTAINERFILES)

check-yaml:
	@command -v yamllint >/dev/null 2>&1 || { echo "yamllint not found — pip install yamllint" >&2; exit 1; }
	yamllint $(YAML_SRCS)

# ---- lint (alias for check, for discoverability) -------------------------- #

.PHONY: lint lint-shell lint-containerfile lint-yaml lint-python

lint: check
lint-shell: check-shell
lint-containerfile: check-containerfile
lint-yaml: check-yaml
lint-python: check-py

# ---- format --------------------------------------------------------------- #

.PHONY: format format-shell format-python

format: format-python format-shell

# Auto-format the Python code (yapf + docformatter + ruff --fix).
# Mirrors the reference `format` target (without the frontend half).
format-python: py-ready
	$(VBIN)/ruff check --fix --exit-zero $(PYTHON_SRCS)
	$(VBIN)/yapf --in-place --recursive $(PYTHON_SRCS)
	$(VBIN)/docformatter --in-place --recursive $(PYTHON_SRCS) || [ $$? -eq 3 ]

format-shell:
	@command -v shfmt >/dev/null 2>&1 || { echo "shfmt not found — apt install shfmt" >&2; exit 1; }
	shfmt -w $(SHFMT_FLAGS) $(SHELL_SRCS)
	shfmt -w $(SHFMT_FLAGS) -ln posix $(POSTINST_SRCS)

# ---- test (local smoke checks — no container needed) ---------------------- #
# Mirrors docs/testing-quality.md § Smoke checks.

.PHONY: test test-unit

# Unit and static integration tests (pytest).
test-unit: py-ready
	$(VBIN)/pytest -q tests/unit tests/integration

test: py-ready test-unit
	@# 1. Every runtime test has a diag; counts must match.
	@name_count=$$(grep -c '^  - name:' workflows/tests.yml); \
	 diag_count=$$(grep -c '^    diag:' workflows/tests.yml); \
	 if [ "$$name_count" -ne "$$diag_count" ]; then \
	   echo "FAIL: workflows/tests.yml — $$name_count names, $$diag_count diags" >&2; \
	   exit 1; \
	 fi; \
	 echo "OK  test manifest integrity ($$name_count tests, $$diag_count diags)"
	@# 2. Syntax-check the installer recipe generator.
	python3 -m py_compile $(PYTHON_SRCS)
	@echo "OK  gen-recipe.py syntax"
	@# 3. Ruff lint gate.
	$(VBIN)/ruff check $(PYTHON_SRCS)
	@echo "OK  ruff"
	@# 4. Warn when bootc-debs-builder inputs changed without a sources/env update.
	@if git diff --name-only 2>/dev/null | grep -q 'workflows/bootc-debs-builder/'; then \
	   echo "INFO: bootc-debs-builder files modified — confirm sources/env declared in packages.yml"; \
	 fi

# ---- docs (KT-2) --------------------------------------------------------- #
# Generates docs/reference/ from the Python docstrings and the shell header
# comments. `docs-check` fails when the committed pages are stale (CI gate).
# Unlike the reference, ast + regex replace pydoc-markdown: the file names
# contain hyphens, which pydoc-markdown cannot import.

.PHONY: docs docs-check

docs:
	python3 scripts/gen_docs.py

docs-check:
	python3 scripts/gen_docs.py --check

# ---- build ---------------------------------------------------------------- #

.PHONY: build

build:
	podman build --format docker \
	  --build-arg PRODUCT_NAME="debian bootc" \
	  -f Containerfile -t debian-bootc:local .

# ---- end-to-end boot test (needs podman, sudo, /dev/kvm; Debian/Ubuntu host) - #

.PHONY: e2e

# Usage: make e2e IMAGE=debian-bootc:local [ARCH=amd64]
e2e:
	scripts/e2e-local.sh "$(IMAGE)" "$(or $(ARCH),amd64)"

# ---- help ----------------------------------------------------------------- #

.PHONY: help all

all: check test

help:
	@echo "Targets:"
	@echo "  make admission            — install Python lint/type/security tools into .venv"
	@echo "  make check                — full gate: yapf + docformatter + ruff + mypy +"
	@echo "                              basedpyright + pydoclint + bandit + shellcheck +"
	@echo "                              hadolint + yamllint"
	@echo "  make check-py             — Python gate only"
	@echo "  make check-shell          — shellcheck only"
	@echo "  make check-containerfile  — hadolint only"
	@echo "  make check-yaml           — yamllint only"
	@echo "  make lint                 — alias for check"
	@echo "  make format               — yapf + docformatter + ruff --fix + shfmt"
	@echo "  make test                 — local smoke checks (no container needed)"
	@echo "  make e2e IMAGE=<ref>      — boot-test a local image like CI (needs /dev/kvm)"
	@echo "  make build                — podman build (amd64 host, full image)"
	@echo "  make docs                 — doc generation (KT-2, not yet implemented)"
