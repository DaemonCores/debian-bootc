# Support

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

Support is provided on a best-effort basis. Debian bootc is a Developer Alpha and its CI/CD is under repair.

- **Questions, ideas, derivative-image discussions:** [organization discussions](https://github.com/orgs/DaemonCores/discussions).
- **Reproducible problems** (the base image, a derived image, the documentation): [GitHub issues](https://github.com/DaemonCores/debian-bootc/issues/new/choose).
- **Vulnerabilities:** never in public; follow [SECURITY.md](SECURITY.md).

## Before opening an issue

Read the [README](README.md) and [architecture documentation](docs/Handoff-Architecture.md), then search existing issues.

Provide:

- image digest or commit;
- `amd64` or `arm64` and the exact hardware or VM type;
- image variant (standard; the NVIDIA stack is the install-time derived lane);
- installation method (direct bootc installation of the OCI image, raw image, or a derived image; installer ISOs are currently known to be broken);
- relevant console, journal, `bootc status`, and failed-unit output;
- reproduction steps and expected result.

## Project scope

The project can investigate its package recipes, image layout, shared pipeline integration, QEMU boot tests, installer generation, first-boot tooling, and project-specific service changes.

Report issues that reproduce on an unmodified Debian installation to Debian. Report downstream-only Proxmox behaviour to `DaemonCores-VE`. Hardware enablement that is not caused by the image may require the relevant kernel or firmware project.

The project does not provide paid support, response-time guarantees, or a hardware compatibility guarantee. Security-sensitive reports belong in the private process described in [SECURITY.md](SECURITY.md).

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
