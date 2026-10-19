# Inconsistencies & tech debt

Index of technical-debt findings for debian-bootc. Each row links to a detail file under [`tech-debt/`](tech-debt/). Last full audit: 2026-10-18 (first audit, so no prior TDs to reconcile).

## Outdated prerequisites

| Component | Pinned in repo | Reality (checked 2026-10-18) | Source |
|---|---|---|---|
| bootupd, bootc, ostree, composefs | latest upstream release, resolved by the CI at each build (`track:` in `packages.yml`) | the last-good published deb is kept when the latest release does not build | `workflows/bootc-debs-builder/packages.yml` |
| Debian base | `debian:trixie` (Debian 13, moving tag) | current Debian stable | `Containerfile:5` |
| Shared CI workflows | `DaemonCores-CI ...@main` | moving branch, no version | `.github/workflows/pipeline.yml:71` |

Upstream releases come from `https://api.github.com/repos/<owner>/<repo>/releases/latest` for bootc-dev/bootc, ostreedev/ostree, coreos/bootupd and composefs/composefs.

## Baseline checklist results

**Containerfiles** (`Containerfile`, `Containerfile.minimal`, `Containerfile.iso`):
- `USER <non-root>`: absent, by design and not a finding. These are bootc OS images (`LABEL containers.bootc=1`, `Containerfile:14`) booted as a root filesystem with systemd as PID 1, not app containers, and the runtime user is created by the first-boot wizard (`workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:233`).
- `display_errors` / `opcache`: N/A, no PHP.
- `HEALTHCHECK`: explicitly `HEALTHCHECK NONE` with a stated reason (`Containerfile:198-199`, `Containerfile.minimal:295`, `Containerfile.iso:107`). OS images have no runtime container healthcheck, so this is satisfied.
- `--no-install-recommends`: missing on the main package install (`Containerfile:101`) → [TD-20261018-full-image-install-recommends](tech-debt/TD-20261018-full-image-install-recommends.md). `rm -rf /var/lib/apt/lists/*` is satisfied globally by the `DPkg::Post-Invoke` hook (`src/debianpreinstall/etc/apt/apt.conf.d/99-apt-clean:1`).
- Base image pinning: moving tags (`Containerfile:5`, `Containerfile.minimal:69`, `Containerfile.iso:28`) → [TD-20261018-unpinned-base-images](tech-debt/TD-20261018-unpinned-base-images.md).
- `ADD <remote-url>`: verified absent. The APT key is fetched with `wget` and checked with `sha256sum -c` (`Containerfile:76-80`).
- Secrets via `ARG`: verified absent. The ARGs are arch/package selectors, a public key digest, `PRODUCT_NAME`, `IMAGE_REGISTRY`, `AUTOUPDATE` and `KERNEL_CMDLINE_SERIAL`.

**docker-compose**: N/A, no compose file in the repo.

**CI** (`.github/workflows/pipeline.yml`, `.github/workflows/docs-wiki-sync.yml`):
- `StrictHostKeyChecking=no`: verified absent in this repo.
- Quality gate before publish: delegated to the shared workflow. `workflows/tests.yml:1-3` states that a failing QEMU test blocks the push, and the shared `bootc-build.yml` confirms it: the "Boot-test the image" step runs before "Push" in the same job, so a test failure stops the push (installer `iso` tag excepted, lint-only) [src: url: https://github.com/DaemonCores/DaemonCores-CI/blob/main/.github/workflows/bootc-build.yml].
- `pull_request_target`: verified absent. The only triggers are push, schedule and workflow_dispatch (`.github/workflows/pipeline.yml:17-26`).
- Pinned action versions: the shared workflows are pinned to the moving `@main` branch → [TD-20261018-reusable-workflow-main-ref](tech-debt/TD-20261018-reusable-workflow-main-ref.md).
- CI secret sourcing: Not evaluated safely (requires Kronn's local secret scanner). Safe signal: neither workflow file references `secrets.` directly; both use `secrets: inherit`.

**`.env*` files**: none tracked (`git ls-files -- '*.env*' '.env*'` is empty). `.env` and `.secrets` are git-ignored (`.gitignore:11-12`) and docker-ignored (`.dockerignore`).

**Web project**: N/A, no HTML templates (the repo is Containerfiles, YAML, shell and one Python script).

**Community standards** (OSS intent: LGPL-2.1 `LICENSE` and a public GitHub remote):
- `LICENSE`: present (LGPL-2.1).
- README description: present (`README.md:18`).
- Issue templates: present (`.github/ISSUE_TEMPLATE/bug_report.yml`, `feature_request.yml`).
- PR template: not in this repo. It is inherited from the org-level `DaemonCores/.github` repo, which ships `PULL_REQUEST_TEMPLATE.md` [src: url: https://github.com/DaemonCores/.github].
- `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`: present at the repo root.

**Repository hygiene**: no tracked package-manager caches, runtime DB/log/dump files or generated review outputs (`git ls-files --cached` checked). `scripts/__pycache__/` exists locally but is untracked, so it is not flagged.

## Current list

| ID | Area | Severity | Status | Summary |
|---|---|---|---|---|
| [TD-20261018-ssh-host-keys-baked-in-image](tech-debt/TD-20261018-ssh-host-keys-baked-in-image.md) | Security | High | **Fixed** | openssh-server postinst bakes host keys into the image; all deployments share the same private key |
| [TD-20261018-dhcp-domain-unsanitized-sed](tech-debt/TD-20261018-dhcp-domain-unsanitized-sed.md) | Security | Medium | **Fixed** | DHCP domain is interpolated unescaped into root sed on `/etc/hosts` (`domain-set:32-36`) |
| [TD-20261018-reusable-workflow-main-ref](tech-debt/TD-20261018-reusable-workflow-main-ref.md) | CI | Medium | Verified in source | Shared workflows called `@main` with `secrets: inherit` and id-token write |
| [TD-20261018-unverified-build-downloads](tech-debt/TD-20261018-unverified-build-downloads.md) | Security | Medium | Verified in source | yq/gh `latest`, `curl \| sh` rustup, ostree tarball without checksum |
| [TD-20261018-hardcoded-public-dns](tech-debt/TD-20261018-hardcoded-public-dns.md) | Other | Medium | **Fixed** | ifupdown2 autoconf forces Cloudflare/Google DNS on every host |
| [TD-20261018-unpinned-base-images](tech-debt/TD-20261018-unpinned-base-images.md) | Infra | Low | Verified in source | `FROM debian:trixie` / `:latest-<arch>-autoupdate` without digest (documented trade-off) |
| [TD-20261018-full-image-install-recommends](tech-debt/TD-20261018-full-image-install-recommends.md) | Infra | Low | Verified in source | `Containerfile:101` installs ~50 packages with Recommends |
| [TD-20261018-bootc-stack-behind-upstream](tech-debt/TD-20261018-bootc-stack-behind-upstream.md) | Backend | Low | Verified in source | bootupd/bootc/ostree pins trail upstream; no automated bump |
| [TD-20261018-domain-set-dead-reset-branch](tech-debt/TD-20261018-domain-set-dead-reset-branch.md) | Backend | Low | **Fixed** | Unreachable `resetdomaine` writes `${HOSTS}` (whole file) instead of `${HOST}` |
| [TD-20261018-swallowed-errors-ostree-migration](tech-debt/TD-20261018-swallowed-errors-ostree-migration.md) | Infra | Low | **Fixed** | `&& cp ... \|\| true &&` swallows mkdir failures in the ostree layout phase |
| [TD-20261018-containerfile-phase-duplication](tech-debt/TD-20261018-containerfile-phase-duplication.md) | Infra | Low | Verified in source | SSL/APT-key/ostree phases copy-pasted between the two Containerfiles |
| [TD-20261018-installer-catalog-arch-bootloader](tech-debt/TD-20261018-installer-catalog-arch-bootloader.md) | Other | Low | Verified in source | gen-recipe.py offers both arches on every ISO and hardcodes `grub2` |
| [TD-20261018-config-and-comment-drift](tech-debt/TD-20261018-config-and-comment-drift.md) | Docs | Low | **Fixed** | `config.yml` comment says default `nosign` while the value is `both`; minimal header names the wrong kernel package |
| [TD-20261018-orphan-polkit-rule-copy](tech-debt/TD-20261018-orphan-polkit-rule-copy.md) | Other | Low | **Fixed** | Duplicate polkit rule under `/etc/rules.d/`, which polkit never reads |

## Dimension coverage

| Dimension | Outcome | Evidence / reason |
|---|---|---|
| Dependencies | findings | bootc stack pins behind upstream (`workflows/bootc-debs-builder/packages.yml:1273`, `:1404`, `:1472`); moving base tags (`Containerfile:5`) |
| Security | findings | unsanitized DHCP domain in sed (`workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:32-36`); `@main` + `secrets: inherit` (`.github/workflows/pipeline.yml:71`, `:84`); unverified downloads (`workflows/env.yml:74-102`, `workflows/bootc-debs-builder/packages.yml:1411-1413`). Also reviewed and found sound: first-boot wizard input validation and `chpasswd` via printf (`firstboot-user-setup:141`, `:160`, `:241-244`), APT key digest check (`Containerfile:76-80`), and the live polkit rule scoped to `org.tunaos.Installer` |
| Code quality | findings | dead/buggy `resetdomaine` (`domain-set:44-58`); `\|\| true` precedence (`Containerfile:179`, `Containerfile.minimal:271`); orphan polkit rule copy. `packages.yml` is 1713 lines, but it is a declarative per-package manifest, not a god-file |
| Scalability | N/A: no long-running service, request path, DB or queue in this repo | Output is OS images and `.deb` packages; the only runtime code is one-shot boot scripts (`bootc-finalize`, `ifupdown2-autoconf`, `domain-set`, `firstboot-user-setup`) |
| Maintainability | findings | hand-synced duplicate phases (`Containerfile.minimal:262`); `scripts/gen-recipe.py` has no tests and hardcodes arch/bootloader (`scripts/gen-recipe.py:33`, `:51`). Runtime tests exist (`workflows/tests.yml`, 42 `- name:` entries) |
| Accessibility (a11y) | N/A: no web UI or library API in this repo | The only interactive surface is the whiptail TTY wizard (`firstboot-user-setup:82-117`); the GTK installer is built from the external `frostyard/bootc-installer` repo (`packages.yml:1633`) |
| Observability | scanned — nothing substantiable | The full image keeps default journald. The minimal image sets `Storage=none` on purpose (`src/minimalpostinstall/etc/systemd/journald.conf.d/00-minimal.conf:2`, `Containerfile.minimal:26`). Boot scripts log to the journal via systemd units; error trackers, metrics and health endpoints do not apply to an OS image (`HEALTHCHECK NONE`, `Containerfile:199`) |
| Compliance | findings | hardcoded Cloudflare/Google DNS (`ifupdown2-autoconf:30`, `:50`). License is LGPL-2.1 (`LICENSE:1`, `Containerfile:13`); a per-package license audit of the built debs was not run (no `cargo deny` / license-checker config in the repo) |
| Performance | findings | Not declared perf-sensitive in `README.md`, but the minimal image targets low idle RAM (`Containerfile.minimal:5-6`). Only finding: Recommends pulled into the full image (`Containerfile:101`) |
| Documentation drift | findings | `config.yml:4` vs `config.yml:11`; `Containerfile.minimal:11-19` vs `:107`; `Containerfile:170`. The docs written this audit were cross-checked: the `docs/testing-quality.md` claim of 35 tests matches `workflows/tests.yml`, and the cited paths resolve |

## Coverage gaps

- The shared pipeline `DaemonCores/DaemonCores-CI` (job graph, quality gate, privileged ISO jobs, secret handling) is outside this repo and was not audited.
- Whether ISC dhclient escapes `|`, `&` or `;` in the `domain-name` it writes to the lease file decides how severe [TD-20261018-dhcp-domain-unsanitized-sed](tech-debt/TD-20261018-dhcp-domain-unsanitized-sed.md) is. This was not tested.
- No Medium findings were trimmed; total is 13 (4 Medium, 9 Low).

## Reconciliation candidates

None. `docs/tech-debt/` did not exist before this audit, so there are no previous TDs.
