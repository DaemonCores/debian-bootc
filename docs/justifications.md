# Design decisions and trade-offs

This document records decisions visible in the current codebase. It separates implemented behaviour from future plans.

## Debian 13 as the base

Debian 13 (Trixie) is the current base image. It provides the package ecosystem used by the project, but Debian does not provide the complete bootc stack required here. The missing components are therefore built and published by this repository.

Using the moving `debian:trixie` image means rebuilds receive upstream fixes without manually changing a digest. It also means a rebuild can change when the Containerfile has not. The pipeline's runtime tests and scheduled rebuilds are intended to detect that integration drift.

## Native Debian packages for the bootc stack

bootc, OSTree, composefs, bootupd, and the bootloader integration are packaged as Debian packages instead of copied into the final image as loose build artifacts.

This gives APT-visible versions, declared dependencies, repeatable image assembly, and a reusable package repository. It also makes the packaging layer a security boundary: package recipes, upstream references, generated maintainer scripts, and signing credentials require review.

## dracut and BLS-capable GRUB on amd64

The image uses dracut for the bootc/OSTree initramfs path. The amd64 EFI stack uses a GRUB build with the BLS modules required by the deployment model, then stages Secure Boot assets through the custom package.

This replaces parts of Debian's conventional boot path. The package build and QEMU tests must therefore cover bootloader files, initramfs generation, and deployment metadata rather than assuming a successful package installation is sufficient.

## OSTree filesystem layout

The image redirects mutable top-level directories into `/var` while the operating-system deployment supplies `/usr`. This is required for transactional replacement of the system tree without discarding host state.

Any downstream image must preserve those links. Replacing them with ordinary directories can make an image build successfully but fail at installation or upgrade time.

## Two networking profiles

The full image uses ifupdown2 because it is also the networking model expected by the Proxmox downstream. The package carries bootc-specific ordering and first-boot autoconfiguration.

The minimal image uses systemd-networkd to reduce dependencies and background processes. This is an intentional image-level difference, not two interchangeable configurations.

## Content-addressed package reuse

Package builds hash their declared sources, upstream version, build script, and non-secret environment. An unchanged package is restored from the last published cache.

The cache reduces rebuild time, but its correctness depends on complete source declarations in `packages.yml`. Adding an undeclared input can produce a stale reuse. Package changes must therefore update the manifest's `sources` field when necessary.

## QEMU tests before publication

Static image validation cannot prove that the bootloader, initramfs, deployment, networking, and system services work together. The pipeline installs the image to a virtual disk and tests the running system over SSH before pushing it.

The tests validate the virtualized reference environment. Hardware-specific firmware, storage controllers, Secure Boot enrollment, SBC boot firmware, and unusual network devices still require separate qualification.

## First-boot credential provisioning

The current Kickstart performs the storage and bootc deployment without embedding a default root password. The console first-boot wizard creates the initial user and sets the root password with `chpasswd` before marking setup complete.

This avoids a shared fallback credential, but makes the tty1 setup path part of system recovery. Changes to the getty drop-in or wizard must be tested for interruption and restart behaviour so a failed setup cannot leave the host permanently inaccessible.

## Keyless image signing

Published images are signed with cosign using the GitHub Actions OIDC identity. This avoids a long-lived container-signing private key in repository secrets and binds the signature to the workflow identity.

Consumers must still verify the expected issuer and workflow identity. A valid Sigstore signature from an unexpected repository or workflow is not sufficient.

## GitHub Action references

The repositories currently use major-version tags for third-party actions and `@main` for the shared DaemonCores workflows. Dependabot assists with updates, but tags and branches are mutable references.

This favours maintenance speed over commit-level immutability. Before calling the pipeline interface stable, shared workflows should be versioned and security-sensitive third-party actions should be evaluated for commit pinning.

## Privileged image creation

ISO and raw-disk creation require loop devices, mounts, partitioning, and filesystem tools. Those jobs run with elevated container privileges.

Keep these jobs isolated from untrusted pull-request code and do not expose write-capable credentials to workflows that can execute arbitrary contributor changes.
