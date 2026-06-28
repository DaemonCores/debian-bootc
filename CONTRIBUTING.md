# Contributing to debian-bootc

Thank you for your interest in contributing! This document outlines the process for reporting bugs, proposing features, and submitting changes.

## Reporting Bugs

If you encounter a bug, please open a [Bug Report](https://github.com/DaemonCores/debian-bootc/issues/new?template=bug_report.yml) and fill out the form completely. Include:

- The exact version of the image you are running.
- The deployment type (online ISO, offline ISO, or direct container).
- Clear steps to reproduce the issue.
- Relevant logs or command output.

## Proposing Features

Feature requests are tracked as GitHub issues. To propose a new feature or enhancement, open a [Feature Request](https://github.com/DaemonCores/debian-bootc/issues/new?template=feature_request.yml) and describe:

- The problem you are trying to solve.
- The solution you would like to see.
- Any alternatives you have considered.

## Development Environment

debian-bootc is built as a `bootc`/`ostree` image. The main artifact is the `Containerfile`.

### Prerequisites

- [Podman](https://podman.io/) or Docker
- [bootc](https://github.com/bootc-dev/bootc) (for local testing)
- A Debian Trixie system or container for package build testing

### Local Build

```bash
podman build -t debian-bootc:latest -f Containerfile .
```

### Lint

```bash
bootc container lint
```

### Testing the APT repository locally

```bash
# After running bootc-debs-builder, the APT repo is published to GitHub Pages
# You can also test locally by pointing apt at a local file server
```

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

Format:

```
<type>(<scope>): <subject>
```

Common types:

- `feat`: new feature or enhancement
- `fix`: bug fix
- `docs`: documentation only changes
- `style`: formatting, missing semicolons, etc.
- `refactor`: code change that neither fixes a bug nor adds a feature
- `chore`: build process or auxiliary tool changes

Example:

```
feat(iso): add offline installer kickstart template
```

## Review Process

All contributions are reviewed via GitHub Pull Requests. Before submitting:

1. Ensure your branch is up to date with `main`.
2. Describe the motivation and scope of the change in the PR description.
3. Reference any related issues using `Fixes #<issue_number>` or `Relates to #<issue_number>`.

A maintainer will review the PR, request changes if needed, and merge once approved.

## Security

If you discover a security vulnerability, please see [SECURITY.md](SECURITY.md) for the responsible disclosure process.

## Questions?

For general support questions, please check [SUPPORT.md](SUPPORT.md) first.
