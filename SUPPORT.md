# Support

## Where to Get Help

### Documentation

The [debian-bootc Wiki](https://github.com/DaemonCores/debian-bootc/wiki) contains the latest documentation, build instructions, and troubleshooting guides.

### GitHub Issues

If you encounter a bug or want to request a feature, please use the GitHub issue forms:

- [Bug Report](https://github.com/DaemonCores/debian-bootc/issues/new?template=bug_report.yml)
- [Feature Request](https://github.com/DaemonCores/debian-bootc/issues/new?template=feature_request.yml)

Before opening an issue, please search existing issues to avoid duplicates.

## What Is Supported

We provide community support for:

- Building and deploying the debian-bootc image.
- ISO installer generation (online and offline).
- First-boot configuration and the `firstboot-user-setup` wizard.
- General bootc/ostree lifecycle operations (`bootc update`, `bootc rollback`, etc.).
- The APT repository and package updates.
- Networking configuration with `ifupdown2`.
- Secure Boot MOK enrollment and troubleshooting.

## What Is NOT Supported

The following are explicitly out of scope for community support:

- **Upstream Debian bugs**: Issues that are reproducible on a standard Debian Trixie installation (without bootc/ostree) should be reported to the [Debian Bug Tracking System](https://bugs.debian.org/) directly.
- **Hardware-specific issues unrelated to the image**: Driver or firmware problems that are not specific to the atomic deployment model.
- **Downstream project issues**: Bugs specific to layers built on top of debian-bootc (e.g., Proxmox-Atomic) should be reported to their respective repositories.
- **Paid enterprise support**: This is a community-maintained project. For professional support, consider commercial vendors offering Debian or bootc consulting.

## Response Expectations

This is a community-maintained project. Responses to issues and discussions are best-effort and may take several days depending on maintainer availability.

For urgent or security-sensitive matters, please refer to [SECURITY.md](SECURITY.md).
