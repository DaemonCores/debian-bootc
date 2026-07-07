# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in debian-bootc, please report it privately.

- **Email**: `guillou.gabriel@gmail.com` (PGP key available on request)
- **GitHub Private Vulnerability Reporting**: Use [GitHub Security Advisories](https://github.com/DaemonCores/debian-bootc/security/advisories/new)

Please do **not** open public issues for security vulnerabilities.

## Supported Versions

| Version | Supported          |
|---------| ------------------ |
| latest  | :white_check_mark: |
| < latest| :x:                |

Only the latest published image is actively maintained with security updates. Users are expected to pull the latest image or rebuild from the latest source.

The current target base is **Debian 13 Trixie**.

## Response Timeline

- **Acknowledgement**: Within 48 hours of receiving a report.
- **Initial Assessment**: Within 5 business days.
- **Patch and Disclosure**: Coordinated with the reporter. We aim to release a fix within 30 days of acceptance, or sooner for critical issues.

## Disclosure Process

1. Reporter submits vulnerability privately.
2. Maintainers confirm receipt and begin assessment.
3. If accepted, a fix is developed in a private branch.
4. A GitHub Security Advisory is drafted.
5. The fix is merged, a new image is built, and the advisory is published simultaneously.

## Known Risks

### Default Root Password

The kickstart installer sets a temporary default root password `BootcDebug@0` as a deliberate fallback. This password is intended to be replaced by the `firstboot-user-setup` wizard on the first successful boot. Leaving this password unchanged beyond first boot is a known security risk. See the [README](README.md#default-root-password) for details.

### Secure Boot MOK Enrollment

The `grub-efi-amd64-signed` package queues MOK enrollment automatically on package install. On first boot after installation, the user must manually confirm enrollment in the MokManager screen. If enrollment is skipped, Secure Boot remains partially disabled for GRUB.

The signing certificate is shipped at `/usr/share/debian-bootc/sb_signing.crt`. The private key (`SB_SIGNING_KEY`) used to sign GRUB must be kept secure. If compromised, an attacker could sign malicious EFI binaries that pass Secure Boot verification.

### Container Image Signing

The OCI container image is signed with [cosign](https://github.com/sigstore/cosign) via keyless Sigstore signing using the GitHub Actions OIDC identity. The signature is stored in the same GHCR namespace as the image.

Verify a pulled image before trusting it:
```bash
cosign verify ghcr.io/DaemonCores/debian-bootc:latest \
  --certificate-identity-regexp \
    "https://github.com/DaemonCores/DaemonCores-CI/.github/workflows/bootc-build.yml@refs/heads/main" \
  --certificate-oidc-issuer \
    "https://token.actions.githubusercontent.com"
```

Always verify the image signature before deployment, especially in air-gapped or security-sensitive environments.
