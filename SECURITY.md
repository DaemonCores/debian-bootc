# Security policy

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

## Private reporting

Use [GitHub private vulnerability reporting](https://github.com/DaemonCores/debian-bootc/security/advisories/new) or email `guillou.gabriel@gmail.com`. Do not open a public issue for an undisclosed vulnerability.

Include the affected commit or image digest, architecture, installation path, impact, reproduction steps, and relevant logs with secrets removed.

## Supported state

The project is under active development. Security fixes target the current default branch and the newest artifacts produced from it. There is no versioned long-term-support branch; older images and installer media should be treated as unsupported.

## Important security boundaries

- The image trusts the project APT key only after checking its pinned digest.
- Published images are signed with the GitHub Actions OIDC identity; consumers should verify both issuer and expected workflow identity.
- Secure Boot signing keys are repository secrets and must never appear in artifacts or logs.
- Installer jobs and bootc installation perform privileged disk operations.
- The current installer does not embed a shared root password; the tty1 first-boot wizard provisions the initial user and root credentials.
- Runtime tests reduce integration risk but do not certify arbitrary hardware.

Reports involving the package cache, signature verification, installer target selection, credential masking, boot chain, or writable-state boundaries are in scope.

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
