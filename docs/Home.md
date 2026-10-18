# debian-bootc documentation

`debian-bootc` builds and tests a Debian 13 bootc/OSTree operating-system image and the Debian packages required to support it.

## Documentation map

- [Architecture](architecture.md) — package, image, test, publication, and installation flow.
- [Design decisions](justifications.md) — decisions that carry operational or security trade-offs.
- [Minimal image](minimal.md) — exact scope and configuration of `Containerfile.minimal`.
- [Decisions](decisions.md) — intentional choices with the anti-pattern to avoid.
- [Architecture overview](architecture/overview.md) — build artifacts, CI stages, diagrams and sequences.
- [Repo map](repo-map.md) — folder tree, entrypoints and generated files.
- [Coding rules](coding-rules.md) — per-language conventions and known mistakes.
- [Tech debt](inconsistencies-tech-debt.md) — audit findings, one detail file per entry under `tech-debt/`.
- [Glossary](glossary.md) — project terms, external services and abbreviations.
- [Testing & quality](testing-quality.md) — build checks, runtime boot tests, untested areas.
- [Debug & operations](operations/debug-operations.md) — build/deploy/log commands and common failures.
- [Repository README](https://github.com/DaemonCores/debian-bootc#readme) — status, quick start, and required configuration.
- [Support](https://github.com/DaemonCores/debian-bootc/blob/main/SUPPORT.md) — support channels and issue requirements.
- [Security policy](https://github.com/DaemonCores/debian-bootc/blob/main/SECURITY.md) — private vulnerability reporting.

The Markdown files in `docs/` are the source of truth. The documentation workflow mirrors them to the GitHub wiki.
