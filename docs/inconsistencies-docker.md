# Docker & container inconsistencies

Scope: `Containerfile`, `Containerfile.minimal`, `Containerfile.iso`, `.dockerignore`, `.github/workflows/pipeline.yml`. No `docker-compose*.yml` / `compose*.yaml` in the repo, so section B (compose) is not applicable.

The images are bootc/ostree **bootable OS images** (`LABEL containers.bootc=1` [src: file: Containerfile:14]), not long-running app containers. Therefore:
- No `USER <non-root>`: N/A. The image is a root filesystem booted by systemd as PID 1 (`STOPSIGNAL SIGRTMIN+3` [src: file: Containerfile:6]).
- `HEALTHCHECK NONE` is set explicitly with a rationale in all three files [src: file: Containerfile:242-243] [src: file: Containerfile.minimal:289-290] [src: file: Containerfile.iso:106-107].
- Multi-stage and `COPY --chown`: N/A. There is no build toolchain stage, and every `COPY` writes OS files that root must own.
- Apt list cleanup is global via `DPkg::Post-Invoke` [src: file: src/debianpreinstall/etc/apt/apt.conf.d/99-apt-clean:1].
- No secrets in `ARG`. The only remote fetch (bootc GPG key) is checked with `sha256sum -c` [src: file: Containerfile:74-78] [src: file: Containerfile.minimal:151-155]. No `ADD <url>`.
- Image tag derivation and push live in the external shared workflow [src: file: .github/workflows/pipeline.yml:71] <!-- TODO: verify — DaemonCores-CI is outside this repo -->.

| ID | Problem | Area | Severity |
|---|---|---|---|
| [TD-20261018-image-vuln-scan-not-evidenced](tech-debt/TD-20261018-image-vuln-scan-not-evidenced.md) | No trivy/grype/snyk scan is visible for the published images. The build runs in the external DaemonCores-CI workflow (`.github/workflows/pipeline.yml:71`). Remediation: confirm the shared workflow has a scan, or add one after the image build. | CI | Medium |
| [TD-20261018-unpinned-base-images](tech-debt/TD-20261018-unpinned-base-images.md) | `FROM debian:trixie` and `FROM ...:latest-${ARCH}-autoupdate` use no digest (`Containerfile:5`, `Containerfile.minimal:68`, `Containerfile.iso:28`), so builds are not reproducible. Remediation: pin the digest and let Dependabot bump it, or record this as an accepted decision. | Infra | Low |
| [TD-20261018-full-image-install-recommends](tech-debt/TD-20261018-full-image-install-recommends.md) | Phase 3 `apt install -y` has no `--no-install-recommends` (`Containerfile:101`), which pulls unreviewed packages into the image. Remediation: add the flag and list the wanted recommends explicitly. | Infra | Low |
| [TD-20261018-dockerignore-incomplete](tech-debt/TD-20261018-dockerignore-incomplete.md) | `.dockerignore` has no `.env*` glob and sends `.kronn/`, `.claude/`, `.mcp.json` and `docs/` into the build context (`.dockerignore:1-10`). Remediation: switch to an allow-list. | Infra | Low |
| [TD-20261018-minimal-bootstrap-tools-retained](tech-debt/TD-20261018-minimal-bootstrap-tools-retained.md) | The minimal image keeps git, curl and wget from Phase 1 (`Containerfile.minimal:126-132`). Only wget is ever used. This adds size and CVE surface. Remediation: drop git and curl, and purge wget after the key fetch. | Infra | Low |
| [TD-20261018-iso-cache-order-recipe-before-apt](tech-debt/TD-20261018-iso-cache-order-recipe-before-apt.md) | `COPY Containerfile*` and the recipe generator run before the apt layer (`Containerfile.iso:56-82`), so any variant edit invalidates the apt cache. Remediation: move the apt install above the recipe-gen steps. | Infra | Low |
