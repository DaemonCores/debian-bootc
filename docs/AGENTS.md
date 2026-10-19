<!-- kronn:doc-version="1.0" -->
<!-- kronn:spec="https://github.com/DocRoms/Kronn/blob/main/docs/conventions/agents-md-format-v1.md" local="docs/conventions/agents-md-format-v1.md" -->
# AI agent context — Entry point

**Project:** debian-bootc — Debian 13 (Trixie) bootc/OSTree OS image built from Containerfiles with Podman, plus custom `.deb` packages (bootc, ostree, composefs, bootupd, GRUB, kernel), a signed APT repository, QEMU boot tests and installer ISOs, driven by the shared DaemonCores-CI GitHub Actions workflows.

## Project parameters

Set once during audit; apply to every `docs/` file.

- Working language: English (code comments, commit messages, identifiers).
- Documentation language: English. This governs new documentation only; preserve every existing document in its current language.
- Ticket language: English.
- Ticket IDs in code comments: not observed in the codebase. <!-- TODO: ask user -->
- Test policy: every change to boot, filesystem, networking or service behaviour adds a runtime test with a `diag` command to `workflows/tests.yml`, gated by `arch`/`variant` when target-specific; tests run on a QEMU boot of the built image and a failure blocks the push. Local tooling in place: `make test` (pytest unit tests for Python and the ifupdown2 boot scripts, manifest checks) and `make e2e IMAGE=<ref>` (CI boot harness on a local image, needs `/dev/kvm`) — see [testing-quality](testing-quality.md). Still missing: build-level integration tests, see [quality-targets](conventions/quality-targets.md).

> **Rules:** Use the project parameters above; never force-translate an existing document. Update `docs/` after learning something new.
> **MCP:** No MCP server docs exist in this project yet (`docs/operations/mcp-servers/` is absent); if one is added later as `docs/operations/mcp-servers/<name>.md`, read it before calling that MCP tool.
> **Skills and Kronn resources index:** `kronn/INDEX.md` (no-op if the project has none published yet).

---

<!-- kronn:section name="anti-hallu" curated="ai" owner="audit" audit="2026-10-18" -->
## 0. Anti-Hallucination Protocol

Never state a non-trivial technical fact (paths, APIs, config, versions, behaviour) without proof — read the code, then `docs/`, then official docs, then ask; never guess. Cite every assertion as `[src: file: <path>:<line>]` or `[src: url: <url>]`; a citation that doesn't resolve is rejected as fabricated.

Full grammar and cascade: [agents-md-format v1](https://github.com/DocRoms/Kronn/blob/main/docs/conventions/agents-md-format-v1.md) (no local copy in this repo).
<!-- kronn:section:end -->

---

## 1. Context loading (mandatory)

**T0 — Router (always loaded):** [docs/AGENTS.md](AGENTS.md) (this file). Sufficient for trivial tasks.

**T1 — Routed context:** for a matching common task, load exactly the listed files.

| Task | Files |
|------|-------|
| Change the full image (packages, config overlays) — `Containerfile`, `src/debianpreinstall/`, `src/bootcpreinstall/`, `src/debianpostinstall/` [src: file: CONTRIBUTING.md:30] | [architecture](architecture.md), [justifications](justifications.md) |
| Change the minimal image — `Containerfile.minimal`, `src/minimalpostinstall/` [src: file: Containerfile.minimal:67] | [minimal](minimal.md), [architecture](architecture.md) |
| Add/modify a custom `.deb` — `workflows/bootc-debs-builder/packages.yml` + its overlay dirs [src: file: workflows/bootc-debs-builder/packages.yml:1] | [architecture](architecture.md) |
| Add/fix a runtime boot test — `workflows/tests.yml` [src: file: workflows/tests.yml:1] | [architecture](architecture.md) |
| Installer ISO — `Containerfile.iso`, `src/buildisopreinstall/`, `scripts/gen-recipe.py` [src: file: Containerfile.iso:28] | [architecture](architecture.md) |
| CI triggers / stage selection — `.github/workflows/pipeline.yml` [src: file: .github/workflows/pipeline.yml:71] | [architecture](architecture.md) |
| Versions and release channels (edge on push, stable by hand) — `.github/workflows/release.yml` [src: file: .github/workflows/release.yml:1] | [architecture](architecture.md) |

**T2 — Search:** if T1 does not cover the task, search `docs/` first and load at most 3 relevant files.

| Need | File |
|------|------|
| Documentation map | [Home](Home.md) |
| Repo structure | [architecture § Repository layout](architecture.md#repository-layout) |
| Build, test and publication flow (CI/CD) | [architecture § Build and test flow](architecture.md#build-and-test-flow) |
| Quality checks, test suites, coverage gaps | [testing-quality](testing-quality.md) |
| Design decisions and trade-offs (narrative) | [justifications](justifications.md) |
| Intentional choices + what NOT to do (table) | [decisions](decisions.md) |
| Coding conventions per language | [coding-rules](coding-rules.md) |
| Target tooling, conventions and tests (declared, not yet implemented) | [quality-targets](conventions/quality-targets.md) |
| Folder tree, entrypoints, generated files | [repo-map](repo-map.md) |
| Build artifacts, CI stages, diagrams | [architecture/overview](architecture/overview.md) |
| Build/deploy/log commands, troubleshooting | [debug-operations](operations/debug-operations.md) |
| Known tech debt | [inconsistencies-tech-debt](inconsistencies-tech-debt.md) |
| Project terms and abbreviations | [glossary](glossary.md) |
| Minimal image contract | [minimal](minimal.md) |
| Contribution, commit and PR conventions | [CONTRIBUTING](../CONTRIBUTING.md) |
| Security reporting | [SECURITY](../SECURITY.md) |

If T0–T2 are insufficient, state which additional file you need and why. Never load every file.

`docs/reports/` (not present yet) holds dated audit snapshots when created; it is excluded from T0–T2 routing — read a report only when a task names it.

---

## 2. DO NOT (critical)

- **Add a package build input without declaring it** in that package's `sources`/`env` in `packages.yml` — only declared paths and env are hashed, so the content cache would reuse a stale `.deb` [src: file: workflows/bootc-debs-builder/packages.yml:7] [src: file: CONTRIBUTING.md:47].
- **Install Debian's stock kernel** (`linux-image-amd64`/`linux-image-arm64`) in an image — use `linux-image-${KERNEL_VARIANT}-${ARCH}` from the custom deb; a second `/usr/lib/modules/<kver>/` fails bootc lint [src: file: Containerfile:20].
- **Add a test to `workflows/tests.yml` without a `diag` command** — the harness fails the build if any test lacks one [src: file: workflows/tests.yml:9].
- **Change the APT signing key URL or default digest in only one of `Containerfile` and `Containerfile.minimal`** — both verify the digest (the CI passes `BOOTC_GPG_SHA256` and `BOOTC_APT_URL` as build arguments) [src: file: Containerfile:41] [src: file: Containerfile.minimal:117].
- **Pin `debian:trixie` to a digest** — left unpinned on purpose for automatic security updates [src: file: Containerfile:3].
- **Add job logic to `.github/workflows/pipeline.yml`** — it is a thin caller; the job graph lives in `DaemonCores/DaemonCores-CI` [src: file: .github/workflows/pipeline.yml:3].
- **Guess** when info is missing — say `NOT_FOUND` and ask the user.
- **Invent file paths** — if you don't know where code goes, check [architecture § Repository layout](architecture.md#repository-layout) or ask.
- **Guess tool versions** — if prerequisites are not filled below, ask.
- **Guess languages or frameworks** — check § 6 Stack.
- **Edit auto-generated files** — if a file is marked as generated (e.g., types exported from another language), never edit it by hand.
- **Load all T2 files at once** — max 3, pick what you need.
- **Modify business code** when the task is only about project documentation — edit `docs/` only.
- **Skip the test policy** — see § Project parameters above and § 4.

---

## 3. Prerequisites

| Requirement | Detail |
|-------------|--------|
| Container build tool | Podman with `--format docker` [src: file: README.md:62] |
| Host architecture for local full-image build | amd64 [src: file: README.md:57] |
| Local build command | `podman build --format docker --build-arg PRODUCT_NAME="debian bootc" -f Containerfile -t debian-bootc:local .` [src: file: README.md:62] |
| Network access | Build fetches the signing key and packages from `https://daemoncores.github.io/debian-bootc` [src: file: Containerfile:76] |
| Minimal image build args | `ARCH`, `BOOT_PKG`, `FIRMWARE_PKGS`, `KERNEL_CMDLINE_SERIAL`, `AUTOUPDATE` [src: file: Containerfile.minimal:89] — see [minimal](minimal.md) |
| Package builds | Run in CI inside the `ghcr.io/<owner>/<repo>-buildenv` image defined by `workflows/env.yml` [src: file: workflows/env.yml:5] |
| CI secrets | `PAT_SECRETS` (required for generation), optional `PAT_PKG`; `APT_GPG_KEY`, `SB_SIGNING_KEY`, `SB_SIGNING_CERT` and the cosign and module keys are generated [src: file: README.md:80] |

---

## 4. Constraints

- If no command output: ask user to paste it.
- Pushes touching only `docs/**` or `**.md` do not trigger the build pipeline [src: file: .github/workflows/pipeline.yml:20]; pushes to `docs/**` on `main` are synced to the GitHub wiki [src: file: .github/workflows/docs-wiki-sync.yml:5].
- Architecture- and variant-specific tests must keep their `arch:` (`amd64`/`arm64`) and `variant:` (`main`/`minimal`) gates [src: file: workflows/tests.yml:13] [src: file: CONTRIBUTING.md:49].
- amd64 is the current installation target; arm64 is still being validated [src: file: README.md:20]. CI has been broken since arm64 support work started; arm64 is not functional yet [src: user:pikatsuto:2026-10-18: disc-dc54c008].
- Commits: concise imperative, Conventional Commit prefixes encouraged [src: file: CONTRIBUTING.md:54].

### Test policy

See the Test policy parameter above (§ Project parameters). Test manifest: `workflows/tests.yml` [src: file: workflows/tests.yml:1]; flow: [architecture § Build and test flow](architecture.md#build-and-test-flow).

---

## 5. Source of truth

| What | File(s) |
|------|---------|
| Project documentation | `docs/` |
| Full image definition | `Containerfile` [src: file: Containerfile:5] |
| Minimal image definition (autoupdate/lock variants) | `Containerfile.minimal` [src: file: Containerfile.minimal:114] |
| Installer ISO image | `Containerfile.iso` [src: file: Containerfile.iso:28] |
| Custom `.deb` manifest (names, deps, versions, build scripts) | `workflows/bootc-debs-builder/packages.yml` [src: file: workflows/bootc-debs-builder/packages.yml:12] |
| Package build toolchain image | `workflows/env.yml` [src: file: workflows/env.yml:15] |
| Runtime boot tests | `workflows/tests.yml` [src: file: workflows/tests.yml:24] |
| Kernel base config | `kernel/config` [src: file: workflows/bootc-debs-builder/packages.yml:85] |
| Kernel module selection per target | `kernel/modules/{arm,generic,rk3588,rpi3,rpi4,rpi5,x86_64}` [src: file: workflows/bootc-debs-builder/kernel/modules/x86_64:1] |
| Module signing default | `config.yml` [src: file: config.yml:11] |
| Image APT source for the bootc repo | `src/bootcpreinstall/etc/apt/sources.list.d/debian-bootc.sources` [src: file: Containerfile:71] |
| Installer recipe (image list) | `src/buildisopreinstall/etc/bootc-installer/recipe.json`, regenerated by `scripts/gen-recipe.py` [src: file: scripts/gen-recipe.py:2] |
| CI entry point | `.github/workflows/pipeline.yml` [src: file: .github/workflows/pipeline.yml:71] |

---

## 6. Stack

| Technology | Version | Role |
|------------|---------|------|
| Debian | 13 Trixie (`debian:trixie`, unpinned) [src: file: Containerfile:5] | Base OS for images and build env |
| bootc | latest upstream release, resolved by CI [src: file: workflows/bootc-debs-builder/packages.yml:1273] | Bootable container tooling (built from source) |
| OSTree | latest upstream release, resolved by CI [src: file: workflows/bootc-debs-builder/packages.yml:1180] | Immutable OS deployment |
| composefs (libcomposefs) | latest upstream release, resolved by CI [src: file: workflows/bootc-debs-builder/packages.yml:1121] | Root filesystem integrity |
| bootupd | latest upstream release, resolved by CI [src: file: workflows/bootc-debs-builder/packages.yml:1049] | Bootloader updates |
| GRUB (BLS-capable, signed) | 1+2.12+9+fedora44 [src: file: workflows/bootc-debs-builder/packages.yml:1102] | EFI bootloader (amd64/arm64) |
| bootc-installer | 3.0.0+git0290d4f+bootc7 [src: file: workflows/bootc-debs-builder/packages.yml:1405] | Installer for ISOs |
| fisherman | 0.3.0+git4dc8f1c [src: file: workflows/bootc-debs-builder/packages.yml:1339] | Go tool packaged as `.deb` (requires Go ≥ 1.22) [src: file: workflows/bootc-debs-builder/packages.yml:1345] |
| firstboot-user-setup | 1.0.2 [src: file: workflows/bootc-debs-builder/packages.yml:18] | First-boot user wizard |
| Rust | rustup minimal profile, version unpinned [src: file: workflows/env.yml:101] | Builds bootc/bootupd |
| Podman | unpinned [src: file: README.md:62] | Image build |
| GitHub Actions (DaemonCores-CI reusable `full-pipeline.yml@main`) | `@main` [src: file: .github/workflows/pipeline.yml:71] | CI/CD: debs, APT repo, images, boot tests, cosign, ISOs |
| bootc-image-builder | unpinned [src: file: Containerfile.iso:5] | Converts image to ISO |
| Python 3 | unpinned [src: file: scripts/gen-recipe.py:1] | Installer recipe generation |

---

## 7. Code placement

New code placement: see [architecture § Repository layout](architecture.md#repository-layout).

---

## 8. Code generation

- Search repo for similar implementations first.
- Use [architecture § Repository layout](architecture.md#repository-layout) for file placement.
- Missing/ambiguous info → say `NOT_FOUND`, ask. Never guess.
- Large refactor needed → record it as a new file under `docs/gotchas/` (create the folder if absent) and tell the user.
- **Follow the test policy** — see § 4.
- After task: update `docs/` if you learned something non-obvious. Prefer the agent-writable subfolders: `docs/conventions/`, `docs/gotchas/`, `docs/architecture/`, `docs/operations/`.
- `docs/AGENTS.md` sections use `owner="audit"` or `owner="human"` (legacy `curated="human"` remains protected). Never rewrite a human-owned section in a full or partial audit; re-audits put the proposed change in a dated diff under `docs/reports/`.

---

## 9. Multi-agent config

Redirectors at the project root: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.kiro/steering/instructions.md`, `.vibe/instructions.md`, `.cursorrules`, `.cursor/rules/repo-instructions.mdc`, `.github/copilot-instructions.md`, `.windsurfrules`, `.clinerules`.

Redirectors are stubs pointing to [docs/AGENTS.md](AGENTS.md); all content lives in `docs/`.

---

## 10. Last updated

Project documentation last reviewed: **2026-10-18**.
