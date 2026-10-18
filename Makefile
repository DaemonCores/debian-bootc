# Single entry point for all project actions (KT-1).
# Local runs and CI call the same targets — see docs/conventions/quality-targets.md.
#
# Required tools: shellcheck, shfmt, hadolint, yamllint, ruff
# Install (Debian/Ubuntu): apt install shellcheck shfmt hadolint yamllint
#                          pip install ruff   (or: pipx install ruff)

SHELL := /bin/bash -euo pipefail

# ---- file sets ------------------------------------------------------------ #

SHELL_SRCS := \
	src/buildisopreinstall/sbin/policy-rc.d \
	src/debianpreinstall/usr/sbin/policy-rc.d \
	workflows/bootc-debs-builder/preinstall/usr/sbin/policy-rc.d \
	workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set \
	workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf \
	workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize \
	workflows/bootc-debs-builder/bootcpostinstall/etc/kernel/postinst.d/zz-bootc-finalize \
	workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup

# DEBIAN/postinst scripts use `set -e` (not full pipefail); linted as sh.
POSTINST_SRCS := \
	workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/postinst \
	workflows/bootc-debs-builder/preinstall/output/ostree/DEBIAN/postinst \
	workflows/bootc-debs-builder/preinstall/output/bootupd/DEBIAN/postinst \
	workflows/bootc-debs-builder/preinstall/output/grub-efi-amd64-signed/DEBIAN/postinst \
	workflows/bootc-debs-builder/preinstall/output/grub-efi-arm64-signed/DEBIAN/postinst

CONTAINERFILES := Containerfile Containerfile.minimal Containerfile.iso

YAML_SRCS := \
	config.yml \
	workflows/bootc-debs-builder/packages.yml \
	workflows/env.yml \
	workflows/tests.yml

PYTHON_SRCS := scripts/gen-recipe.py

# ---- guards --------------------------------------------------------------- #
# Each guard prints a hint and exits when the tool is absent so contributors
# see a clear message instead of a cryptic "command not found".

define require
$(if $(shell command -v $(1) 2>/dev/null),,\
  $(error "$(1) not found — install it: $(2)"))
endef

# ---- targets -------------------------------------------------------------- #

.PHONY: all lint lint-shell lint-containerfile lint-yaml lint-python \
        format format-shell format-python \
        test build help

all: lint test

# ---------- lint -----------------------------------------------------------

lint: lint-shell lint-containerfile lint-yaml lint-python

lint-shell:
	$(call require,shellcheck,apt install shellcheck)
	shellcheck $(SHELL_SRCS)
	shellcheck --shell=sh $(POSTINST_SRCS)

lint-containerfile:
	$(call require,hadolint,apt install hadolint  # or: brew install hadolint)
	hadolint $(CONTAINERFILES)

lint-yaml:
	$(call require,yamllint,pip install yamllint)
	yamllint $(YAML_SRCS)

lint-python:
	$(call require,ruff,pip install ruff)
	ruff check $(PYTHON_SRCS)

# ---------- format ---------------------------------------------------------

format: format-shell format-python

format-shell:
	$(call require,shfmt,apt install shfmt)
	shfmt -w $(SHELL_SRCS)
	shfmt -w -ln posix $(POSTINST_SRCS)

format-python:
	$(call require,ruff,pip install ruff)
	ruff format $(PYTHON_SRCS)

# ---------- test (local smoke checks) --------------------------------------
# Mirrors docs/testing-quality.md § Smoke checks; runnable without a container.

test:
	$(call require,ruff,pip install ruff)
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
	@# 3. Lint the Python script.
	ruff check $(PYTHON_SRCS)
	@echo "OK  ruff"
	@# 4. Build-script inputs declared: warn if packages.yml was changed without
	@#    a corresponding sources/env update (non-blocking, informational only).
	@if git diff --name-only 2>/dev/null | grep -q 'workflows/bootc-debs-builder/'; then \
	   echo "INFO: bootc-debs-builder files modified — confirm sources/env are declared in packages.yml"; \
	 fi

# ---------- build ----------------------------------------------------------

build:
	podman build --format docker \
	  --build-arg PRODUCT_NAME="debian bootc" \
	  -f Containerfile -t debian-bootc:local .

# ---------- help -----------------------------------------------------------

help:
	@echo "Targets:"
	@echo "  make lint                 — shellcheck + hadolint + yamllint + ruff"
	@echo "  make lint-shell           — shellcheck on bash/sh scripts"
	@echo "  make lint-containerfile   — hadolint on Containerfile*"
	@echo "  make lint-yaml            — yamllint on config/workflow YAML"
	@echo "  make lint-python          — ruff on scripts/gen-recipe.py"
	@echo "  make format               — shfmt + ruff format"
	@echo "  make format-shell         — shfmt on bash/sh scripts"
	@echo "  make format-python        — ruff format on Python"
	@echo "  make test                 — local smoke checks (no container needed)"
	@echo "  make build                — podman build (amd64 host, full image)"
