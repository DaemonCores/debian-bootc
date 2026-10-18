# Inconsistencies — security

Focused security audit (0.8.2), 2026-10-18. Scope: OS image build (Containerfiles, overlays, first-boot scripts) and CI callers. There is no web application, HTTP server, database or auth backend in this repo, so the web-specific checklist items are N/A.

| ID | Problem | Area | Severity |
|---|---|---|---|
| [TD-20261018-ssh-host-keys-baked-in-image](tech-debt/TD-20261018-ssh-host-keys-baked-in-image.md) | openssh-server is installed at build time and nothing removes or regenerates host keys, so all deployments may share a public host key (`Containerfile:136`, `Containerfile.minimal:187`) | Security | High |
| [TD-20261018-no-image-signature-policy](tech-debt/TD-20261018-no-image-signature-policy.md) | cosign-signed images, but no host-side `policy.json`/sigstore requirement while the auto-update timer is enabled (`workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/postinst:6`) | Security | Medium |
| [TD-20261018-reusable-workflow-main-ref](tech-debt/TD-20261018-reusable-workflow-main-ref.md) | Shared workflows called at `@main` with `secrets: inherit` + write/id-token permissions (`.github/workflows/pipeline.yml:57-71`) | CI | Medium |
| [TD-20261018-unverified-build-downloads](tech-debt/TD-20261018-unverified-build-downloads.md) | yq/gh/rustup/ostree fetched without checksum or version pin (`workflows/env.yml:99-102`, `workflows/bootc-debs-builder/packages.yml:1411-1413`) | Security | Medium |
| [TD-20261018-dhcp-domain-unsanitized-sed](tech-debt/TD-20261018-dhcp-domain-unsanitized-sed.md) | DHCP domain interpolated unescaped into a root sed program on `/etc/hosts` (`workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:32-36`) | Security | Medium |

## Checklist results

**Secrets & credentials**
- Tracked `.env*` files: verified absent (`git ls-files -- '*.env*' '.env*'` returns nothing).
- Secret value scan: Not evaluated safely (requires Kronn's local secret scanner).
- CI YAML credential hygiene: Not evaluated safely (requires Kronn's local secret scanner). Structural fact: `.github/workflows/pipeline.yml` and `.github/workflows/docs-wiki-sync.yml` use `secrets:` (both `secrets: inherit`). No docker-compose files exist.
- Private keys/certs (`*.pem`, `*.key`, `*.p12`, `id_rsa*`, `*.pub`, `.ssh/`): verified absent from tracked files.
- `git log --all -S 'BEGIN PRIVATE KEY'`: verified absent, no commits.

**Authentication & sessions**
- Session cookies: N/A, no HTTP service in this project.
- Password storage: passwords are set through `chpasswd` (`firstboot-user-setup:241,244`), which uses the system PAM/`ENCRYPT_METHOD` hash (Debian default yescrypt, hypothesis). There is no custom hashing.
- JWT secret sourcing / hardcoded Bearer: Not evaluated safely (requires Kronn's local secret scanner). No JWT library in the repo.
- Password reset tokens: N/A.
- Live ISO: the `live` user has an empty password (`Containerfile.iso:97`), autologs in on tty1 and gets polkit `YES` only for `org.tunaos.Installer` (`src/buildisopreinstall/etc/polkit-1/rules.d/50-bootc-installer-live.rules:2-4`). This is by design for installer media; the user is not in `sudo`. Not a finding.
- First boot: root SSH password login is opt-in (`firstboot-user-setup:256-262`). Verified present.

**Input validation & injection**
- SQL: N/A, no database.
- Shell: no `eval`/`sh -c` on external input in shipped scripts. The only external-input-into-root-command path is the DHCP domain → sed (TD-20261018-dhcp-domain-unsanitized-sed). The first-boot username is regex-validated (`firstboot-user-setup:160`).
- File paths: `scripts/gen-recipe.py` reads only build-context paths passed by `Containerfile.iso:60-64`. Not user-controlled.
- Templates (XSS): N/A, no HTML templates.
- Deserialization: `scripts/gen-recipe.py` uses `json.load` only. Verified: no pickle/yaml.load.

**Transport & headers**
- HTTPS / HSTS / CSP / X-Frame-Options / nosniff / CORS: N/A, no HTTP server.
- APT transport: Debian sources are rewritten to `https://` at build (`Containerfile:64`) and signed with `Signed-By` keyrings. The project repo key is SHA-256 pinned (`Containerfile.minimal:152-155`). Verified present.

**Dependencies & supply chain**
- Lockfile: N/A for this repo. Rust crates are built from upstream release tarballs, whose lockfiles live outside the repo.
- Dependabot: verified present for `github-actions` and `docker` (`.github/dependabot.yml`). No cargo/deb audit step is wired for the from-source bootc/bootupd/ostree builds (Inferred, see TD-20261018-bootc-stack-behind-upstream in the main TD index).
- Unpinned downloads / git refs: see TD-20261018-unverified-build-downloads and TD-20261018-reusable-workflow-main-ref.

**SSH/CI deploy**
- `StrictHostKeyChecking=no`: verified absent.
- Deploy SSH key rotation: N/A, no SSH-based deploy (publishing goes to GHCR/Pages through the shared workflow).
- `pull_request_target`: verified absent from `.github/workflows/`.
