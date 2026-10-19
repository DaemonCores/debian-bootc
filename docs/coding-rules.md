# Coding rules (AI contract)

> Every rule below cites a file in this repo or a commit. If a rule you need is not here, say `NOT_FOUND`. **Never invent tool names, conventions, or commands.**

> Glossary: [glossary](glossary.md).

## Global

- Prefer smallest diffs. Avoid drive-by refactors.
- Follow existing naming in adjacent code. Avoid generic names (`Helper`, `Utils`).
- **Follow the test policy:** see [AGENTS](AGENTS.md) § Project parameters. The test manifest is `workflows/tests.yml` [src: file: workflows/tests.yml:1].
- **Comment sparingly — explain *why*, never *what*.** A comment earns its place only if it adds what the code can't say: a non-obvious rationale or a real gotcha. Do NOT narrate what the code does, restate the line above, or leave "this is now loaded from X — see Y" pointers the code/ticket already makes obvious. Match the file's existing comment density; a clear name beats a paragraph. Ticket references in code comments: not observed in this repo (see [AGENTS](AGENTS.md) § Project parameters).
- Repo-wide tooling: configured via a root `Makefile` (single entry point for lint, format, test, build — [src: file: Makefile:1]) with per-tool config files: `.shellcheckrc` [src: file: .shellcheckrc:1], `.hadolint.yaml` [src: file: .hadolint.yaml:1], `.yamllint.yml` [src: file: .yamllint.yml:1], `pyproject.toml` (ruff — [src: file: pyproject.toml:1]). The Rust vendoring config is at `workflows/bootc-debs-builder/preinstall/build/rust/config.toml` [src: file: workflows/bootc-debs-builder/preinstall/build/rust/config.toml:1]. CI job logic lives in the external `DaemonCores/DaemonCores-CI` reusable workflow [src: file: .github/workflows/pipeline.yml:71]; local checks run via `make lint` / `make test`. See [quality targets](conventions/quality-targets.md) for the full KT roadmap.

## Containerfile (Podman / Dockerfile syntax)

Files: `Containerfile`, `Containerfile.minimal`, `Containerfile.iso`.

### Tools

- Linter: hadolint, config at `.hadolint.yaml` [src: file: .hadolint.yaml:1]. Run: `make lint-containerfile`. At build time the image is also checked by bootc lint; a second `/usr/lib/modules/<kver>/` directory fails it [src: file: Containerfile:26].
- Formatter: Not configured.
- Type checker: N/A — not used in this project.
- Build / check command: `make build` or directly `podman build --format docker --build-arg PRODUCT_NAME="debian bootc" -f Containerfile -t debian-bootc:local .` [src: file: README.md:62].

### Conventions

- Set the `RUN` shell to strict bash with `SHELL ["/bin/bash", "-euo", "pipefail", "-c"]` [src: file: Containerfile:58] [src: file: Containerfile.minimal:130].
- Split the file into numbered phases, each with a `# ----` banner and a `# Phase N: …` title [src: file: Containerfile:60] [src: file: Containerfile:77] [src: file: Containerfile.minimal:133] [src: file: Containerfile.minimal:148].
- Put the `&&` / `\` chain at the start of each continuation line, and indent package lists one package per line [src: file: Containerfile:64] [src: file: Containerfile.minimal:134] [src: file: Containerfile.iso:65].
- Install prerequisite and module packages with `apt install -y --no-install-recommends` [src: file: Containerfile:65] [src: file: Containerfile.minimal:135] [src: file: Containerfile.iso:66].
- Each `ARG` has a comment above it explaining its values and why it exists [src: file: Containerfile:17] [src: file: Containerfile:21] [src: file: Containerfile:34].
- Templated overlay files carry `{{ ARCH }}` placeholders, which a `RUN sed -i` replaces after `COPY` [src: file: Containerfile:81] [src: file: Containerfile.minimal:156].

### Common mistakes to avoid

- In an `if/else/fi` inside `RUN`, ending the last package line with `\` and no `;` joins `else`/`fi` onto the `apt install` arguments. Terminate the command with `;` before `else`/`fi` [src: commit: c88288c].
- Never start a `RUN` with `&&`. This mistake was hidden by layer caching until a no-cache build exposed it [src: commit: e4b073f].
- The first `apt update` against the project repo must keep its retry loop. The GitHub Pages CDN can serve a new `InRelease` with a stale `Packages.gz`, which gives "Hash Sum mismatch" [src: commit: b24d611] [src: file: Containerfile:104].
- Use the package names actually published in the APT repo. Debian names use hyphens (`linux-modules-x86-64`, not `linux-modules-x86_64`) [src: commit: f35af91]. Do not install packages that have no `packages.yml` entry, e.g. `linux-headers` [src: commit: 7046317].

## Shell (bash / POSIX sh)

Files: overlay scripts under `src/` and `workflows/bootc-debs-builder/*postinstall/`, `DEBIAN/postinst` files, and the `build: |` scripts inside `workflows/bootc-debs-builder/packages.yml`.

### Tools

- Linter: shellcheck, global config at `.shellcheckrc` [src: file: .shellcheckrc:1]. Run: `make lint-shell`. Inline `# shellcheck disable=` directives appear in scripts [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:10] [src: file: workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:60].
- Syntax check: package builds run `bash -n` on shipped scripts as a content check [src: file: workflows/bootc-debs-builder/packages.yml:36].
- Formatter: shfmt. Run: `make format-shell`.
- Type checker: N/A — not used in this project.

### Conventions

- Bash scripts start with `set -euo pipefail` [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:7] [src: file: workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:5] [src: file: workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf:6] [src: file: workflows/bootc-debs-builder/packages.yml:20]. `DEBIAN/postinst` files use `set -e` [src: file: workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/postinst:2] [src: file: workflows/bootc-debs-builder/preinstall/output/ostree/DEBIAN/postinst:2] [src: file: workflows/bootc-debs-builder/preinstall/output/bootupd/DEBIAN/postinst:2].
- Each standalone script opens with a header comment that names it and says what it does [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:3] [src: file: workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:3] [src: file: workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf:3].
- In build scripts, fatal checks use `test … || { echo "ERROR: …" >&2; exit 1; }` [src: file: workflows/bootc-debs-builder/packages.yml:37] [src: file: workflows/bootc-debs-builder/packages.yml:99] [src: file: workflows/bootc-debs-builder/packages.yml:114].
- Every package build ends with a `# Content check:` on its output [src: file: workflows/bootc-debs-builder/packages.yml:34] [src: file: workflows/bootc-debs-builder/packages.yml:412] [src: file: workflows/bootc-debs-builder/packages.yml:898].
- Expand variables with braces and quote them: `"${VAR}"` [src: file: workflows/bootc-debs-builder/packages.yml:23] [src: file: workflows/bootc-debs-builder/packages.yml:36] [src: file: workflows/bootc-debs-builder/packages.yml:98].
- A `# shellcheck disable=` directive comes with a comment saying why [src: file: workflows/bootc-debs-builder/bootcpostinstall/usr/local/bin/bootc-finalize:9] [src: file: workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:60] [src: file: workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:133].

### Common mistakes to avoid

- Under `set -euo pipefail`, do not use `ls <glob>` in `$(…)` to find files that may be missing. A non-match makes bash exit silently. Use `find … -maxdepth 1 -name …`, which returns 0 [src: commit: e6d37cb] [src: file: workflows/bootc-debs-builder/packages.yml:261].
- Do not make `[ test ] && cmd` the last command of a loop body under `set -e`. A false test leaves status 1 and kills the script silently. Use an explicit `if … fi` [src: commit: 6eb3362] [src: file: workflows/bootc-debs-builder/packages.yml:688].
- Do not embed Python heredocs in `packages.yml` build scripts. One failed silently and the build fell back to stale debs. Use pure shell (`printf`, plus a `grep -q` idempotency guard) [src: commit: 396dbc5].
- Use `dpkg-deb -Zgzip`, not `-Zgz`. The buildenv `dpkg-deb` rejects `gz`, and the early exit reused a corrupt old deb [src: commit: 7046317].

## YAML manifests (`packages.yml`, `tests.yml`, GitHub Actions)

### Tools

- Linter: yamllint, config at `.yamllint.yml` [src: file: .yamllint.yml:1]. Run: `make lint-yaml`. The test harness also validates `workflows/tests.yml` and fails the build if any test lacks `diag` [src: file: workflows/tests.yml:9].
- Formatter: Not configured.
- Type checker: N/A — not used in this project.

### Conventions

- Each manifest opens with a comment block that documents its schema field by field [src: file: workflows/bootc-debs-builder/packages.yml:4] [src: file: workflows/tests.yml:5] [src: file: .github/workflows/pipeline.yml:3].
- `packages.yml` entries list `name`, `sources`, `env` and a verbatim `build: |` script [src: file: workflows/bootc-debs-builder/packages.yml:13] [src: file: workflows/bootc-debs-builder/packages.yml:79]. Versions live in `env` [src: file: workflows/bootc-debs-builder/packages.yml:18] [src: file: workflows/bootc-debs-builder/packages.yml:90].
- Every test in `tests.yml` has `name`, `run`, `diag`, and optionally `expect`/`arch`/`variant`. `diag` prints the runtime state with `2>&1 | head`/`tail` [src: file: workflows/tests.yml:30] [src: file: workflows/tests.yml:33].

### Common mistakes to avoid

- When republishing a fixed deb, bump its version suffix (`+bootcN`). Reusing a filename can serve a corrupt CDN-cached deb [src: commit: d3498a5] [src: file: workflows/bootc-debs-builder/packages.yml:905].
- Artifacts that downstream builds need (kernel `.config`, `Module.symvers`) must ship inside the `.deb`. A cache hit restores only the `.deb` from the APT repo [src: commit: 6c75748] [src: file: workflows/bootc-debs-builder/packages.yml:131].

## Python

File: `scripts/gen-recipe.py`, the repo's only Python file [src: file: scripts/gen-recipe.py:1].

### Tools

- Linter: ruff + pydoclint + bandit, config in `pyproject.toml` [src: file: pyproject.toml:1]. Run: `make check-py`.
- Formatter: yapf + docformatter + ruff (--fix). Run: `make format-python`. Config in `pyproject.toml` [src: file: pyproject.toml:1].
- Type checker: mypy + basedpyright (strict mode), config in `pyproject.toml` [src: file: pyproject.toml:1]. Run: `make check-py`.

### Conventions

N/A — a single file is not enough to establish project-wide conventions.

### Common mistakes to avoid

N/A — no Python-specific bug appears in this repo's history.
