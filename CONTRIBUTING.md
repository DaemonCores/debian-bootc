# Contributing to debian-bootc

<p align="center">
  <img src="https://raw.githubusercontent.com/DaemonCores/.github/refs/heads/main/assets/banner.svg" alt="AstralEmu Banner" width="100%"/>
</p>

<p>
  <strong align="left">Foundations for immutable, Debian-based distributions.</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
  
  <em>Bring the atomic operating-system model to the Debian ecosystem, server side included.</em>
</p>

---

Debian bootc is a Developer Alpha: a foundation for building immutable, Debian-based distributions. Its CI/CD is being repaired, so a green pipeline is not yet a reliable signal; say which paths you tested by hand.

## Contributions we are looking for

- Derived images and distributions built on the base, and feedback on how well the template supports them.
- bootc, OSTree, composefs, bootupd and Debian-integration work.
- Packaging and integration of server software from the Debian ecosystem for an atomic model.
- Boot tests, hardware and virtual-machine testing with technical reports.
- Documentation, packages, installer tooling and build tooling.

Pipeline changes (`.github/workflows/`, shared CI interfaces) interact with the ongoing CI rework: open an issue first. Questions and ideas go to the [organization discussions](https://github.com/orgs/DaemonCores/discussions).

## Bug reports

Include the commit or image digest, architecture, image variant, deployment method, reproduction steps, and relevant logs. For boot failures, attach the earliest available console output and state whether the same artifact boots under the project's QEMU test path.

Use the repository issue forms for bugs and feature proposals. Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).

## Development areas

| Area | Main paths |
| --- | --- |
| Image composition | `Containerfile*`, `src/` |
| Package builds | `workflows/bootc-debs-builder/` |
| Build environment | `workflows/env.yml` |
| Runtime tests | `workflows/tests.yml` |
| Pipeline triggers | `.github/workflows/pipeline.yml` |
| Documentation | `README.md`, `docs/` (wiki symlink) |

## AI-assisted development

The project is developed with extensive use of AI coding assistants for implementation, testing, documentation and debugging. Architecture, requirements, integration decisions and acceptance remain the maintainer's responsibility, and results are validated by real tests, not by successful compilation alone. The maintainer does not claim a line-by-line review of generated code.

If you contribute AI-assisted changes, say so in the pull request, state how you verified them, and be able to answer for them. Only a human may add `Signed-off-by`.

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
- Update the relevant README and wiki page (`docs/` is the wiki) in the same pull request.
- State which architectures and installation paths were actually tested.

Use concise imperative commits; Conventional Commit prefixes are encouraged.

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
