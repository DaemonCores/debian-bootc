# debian-bootc

**The first fully integrated, production-ready Debian 13 (Trixie) bootc image.**

debian-bootc delivers a complete, atomic, rollback-capable Debian operating system built as an OCI container image. It is the base layer for downstream projects like [DaemonCores-VE](https://github.com/DaemonCores/DaemonCores-VE). Every previous attempt to run bootc on Debian either stopped at a proof-of-concept stage or was quietly abandoned — this repository solves the problem end-to-end with automated CI builds, signed APT packages, and installer ISOs.

This wiki is kept in sync with the repository via CI. For the full project documentation, see the [README](https://github.com/DaemonCores/debian-bootc/blob/main/README.md).

## Wiki Pages

- [Architecture](architecture.md) — Layered composition, CI/CD build pipeline, runtime first-boot flow, and key design decisions.
- [Justifications](justifications.md) — Honest explanations for controversial or non-obvious design choices (default root password, Fedora GRUB fork, dracut instead of initramfs-tools, and more).
