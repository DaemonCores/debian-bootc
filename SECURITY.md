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

## How the rolling kernel is elected — trust model

The kernel and the third-party patches move by automatic election, without a human reviewing each diff. The doctrine is reactivity over review: the version is NEVER pinned by hand — each build the `upstream-track` election resolves the newest candidate whose full patch set applies, and the automatic security gates judge it:

- **Care delay** (`CARE_DELAY`, default 24 h, `0` = hotfix): a freshly published candidate is held until its age clears the delay, so a same-day regression upstream does not ship the hour it lands. The hold reason is written to the election log.
- **Flux gate**: OSV.dev and the GHSA advisory stream of each source repository are consulted at resolution. An open advisory on the source or the elected commit holds the build (the last-good deb stays published) and opens a deduplicated issue. An unreachable advisory source degrades to a loud logged pass — the gates never black out the build on their own outage.
- **Bypass**: an actively exploited kernel CVE listed in CISA KEV (or a CRITICAL linux-cve-announce announce) lifts the care delay so the fix ships immediately; the election log cites the CVE ids and the feed.
- **Traceability**: every adopted election is logged (`selection.log`) and published as `sbom.json` + `CHANGELOG.md` at the repository Pages root: each kernel, module and patch carries its URL, sha256, election date and gate verdicts.

The honest consequence of the trust model:

- 'security' means the RECENT MAINLINE kernel with the shipped patch profile — not a distribution-patched LTS. CVEs are handled by the mainline release train, not by cherry-picks.
- The patches are third-party sources (lore mboxes, mirrors) verified by sha256 pin, dry-run and test builds — never by human review of every diff. The gates above catch known-bad content; unknown content ships with mainline trust.
- Support is a best-effort COMMUNITY effort: nothing here is a guaranteed SLA, and a held build keeps the last-good deb until the gate clears.

## Important security boundaries

- The image trusts the project APT key only after checking its pinned digest.
- Published images are signed with a cosign key owned by the repository (repository secrets); the images ship its public key and a policy so hosts only accept signed updates. The private key must never appear in artifacts or logs.
- Secure Boot signing keys are repository secrets and must never appear in artifacts or logs.
- Installer jobs and bootc installation perform privileged disk operations.
- The current installer does not embed a shared root password; the bootc-installer system step provisions the initial user, root password, sudo and SSH policy at install time (the tty1 first-boot wizard is removed).
- Runtime tests reduce integration risk but do not certify arbitrary hardware.

Reports involving the package cache, signature verification, installer target selection, credential masking, boot chain, or writable-state boundaries are in scope.

---

<p>
  <strong align="left">Made with ⭐ by the DaemonCores community</strong>
  <a href="https://github.com/DaemonCores/debian-bootc/wiki"><img align="right" src="https://img.shields.io/badge/Wiki-FFFFFF?style=for-the-badge&logoColor=white" alt="Documentation"/></a>
  <a href="https://github.com/orgs/DaemonCores/discussions"><img align="right" src="https://img.shields.io/badge/Community-000000?style=for-the-badge&logoColor=white" alt="Community"/></a>
  <a href="https://github.com/DaemonCores/debian-bootc"><img align="right" src="https://img.shields.io/badge/Base_debian_for_all_project-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian Bootc"/></a>
</p>
