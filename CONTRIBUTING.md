# Contributing to debian-bootc

<p align="center">
  <img src="https://raw.githubusercontent.com/DaemonCores/.github/refs/heads/main/assets/banner.svg" alt="AstralEmu Banner" width="100%"/>
</p>

<p>
  <strong align="left">Simplify and Innovate for Everyone.</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
  
  <em>Identify gaps and fill them, make improvements where possible, but above all, empower developers to offer more to users.</em>
</p>

---

Contributions are welcome for packaging, image composition, boot tests, installer tooling, and documentation.

## Bug reports

Include the commit or image digest, architecture, image variant, deployment method, reproduction steps, and relevant logs. For boot failures, attach the earliest available console output and state whether the same artifact boots under the project's QEMU test path.

Use the repository issue forms for bugs and feature proposals. Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).

## Development areas

| Area | Main paths |
| --- | --- |
| Image composition | `Containerfile*`, `src/` |
| Package builds | `workflows/bootc-debs-builder/` |
| Build environment | `workflows/build-env/env.yml` |
| Runtime tests | `workflows/image-tests/tests.yml` |
| Pipeline triggers | `.github/workflows/pipeline.yml` |
| Documentation | `README.md`, `docs/` |

## Local image build

```bash
podman build --format docker -f Containerfile -t debian-bootc:local .
```

This consumes the project's published APT repository. Package changes should be tested through the manifest-driven package workflow or an equivalent local package build before testing the final image.

## Change requirements

- Declare every package build input in `packages.yml` so the content cache cannot reuse stale output.
- Add a runtime test and diagnostic command when changing boot, filesystem, networking, or service behaviour.
- Preserve architecture gates for architecture-specific tests.
- Keep secrets out of build logs, fixtures, and issue attachments.
- Update the relevant README and `docs/` page in the same pull request.
- State which architectures and installation paths were actually tested.

Use concise imperative commits; Conventional Commit prefixes are encouraged.

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
