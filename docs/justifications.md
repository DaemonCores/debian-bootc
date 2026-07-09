# Justifications

**Honest explanations for controversial or non-obvious design choices in debian-bootc.**

This document follows a transparency principle: every decision that could be questioned is documented here with its rationale, its risks, and the alternatives.

---

## 1. Default Root Password (`BootcDebug@0`)

### What we do

The Kickstart installer sets a temporary default root password: `BootcDebug@0`.

### Why it exists

This is a **deliberate fallback**, not an oversight. The `firstboot-user-setup` wizard runs on first boot before the login prompt and asks the user to set a root password. If that wizard fails to run — because the TTY is unavailable, the service crashes, or the boot is interrupted — the system would be completely inaccessible without a known fallback credential.

The password serves the same role as the default passwords on Raspberry Pi OS, cloud images, and virtually every other pre-installed Linux image: it guarantees you are not locked out of your own machine before you've had a chance to configure it.

### What happens on first boot

1. The `firstboot-user-setup` wizard prompts for a root password
2. The user-supplied password replaces `BootcDebug@0`
3. `chage -d 0` is applied, forcing the root account to change its password on the next login
4. The temporary password never survives first boot

### Risks

- If the wizard is bypassed and the user does not log in as root, the temporary password remains active until someone does. This is why the wizard is wired into `getty@tty1.service` as `ExecStartPre` — it is nearly impossible to reach a login prompt without passing through it.
- The password is documented in the README and in this file. This is intentional: security through obscurity would be worse. The password is meant to be temporary and replaced, not secret.

### Alternative

Remove the fallback entirely and trust that `firstboot-user-setup` will never fail. We rejected this because a single failure mode (e.g., serial console without `tty1`) would render the installed system unrecoverable without physical access to the boot media.

---

## 2. Fedora GRUB Fork (rhboot/grub2)

### What we do

Instead of using the standard Debian `grub-efi-amd64-signed` package, this repository compiles GRUB from the [Fedora rhboot/grub2](https://github.com/rhboot/grub2) fork at a pinned commit.

### Why it is necessary

The standard Debian GRUB package does not include the `blscfg` and `blsuki` modules required by ostree and bootc for [BLS](https://uapi-group.org/specifications/specs/boot_loader_specification/) (Boot Loader Specification) kernel entry management. Without these modules, bootc cannot generate or manage bootloader entries, breaking the atomic update and rollback model.

### Risks

- The Fedora fork may diverge from upstream GRUB in ways that introduce bugs or incompatibilities. The commit is pinned and the build is smoke-tested.
- Maintenance burden: upstream Debian GRUB security updates must be tracked and backported if they affect the fork.

### Alternative

Patch the Debian GRUB package to add BLS modules. This would require maintaining a Debian-specific patch set against a moving upstream, which is arguably more work than tracking the already-BLS-enabled Fedora fork.

---

## 3. dracut Instead of initramfs-tools

### What we do

This image uses [dracut](https://github.com/dracut-ng/dracut-ng) to generate the initramfs, rather than Debian's default `initramfs-tools`.

### Why it is necessary

1. **bootc/ostree module support** — dracut ships with first-class modules for `bootc`, `ostree`, and `lvm` that are maintained upstream and integrated with the bootc ecosystem. `initramfs-tools` has no equivalent ostree integration.
2. **Host-only vs generic** — dracut supports `hostonly=no`, which produces an initramfs that works on any hardware. This is critical for a container image that may be deployed to diverse bare-metal and VM targets.
3. **Container build integration** — The initramfs is built inside the container during the `bootc` package post-install hook (`bootc-finalize`), producing a fully self-contained deployed image.

### Risks

- dracut is not the Debian default, so some Debian-specific hooks or configurations may not be applied automatically.
- The module list (`bootc`, `lvm`, `ostree`) must be kept in sync with upstream dracut changes.

### Alternative

Use `initramfs-tools` and write custom hooks for ostree/bootc support. This would require maintaining a significant amount of custom initramfs logic that dracut already provides upstream.

---

## 4. ifupdown2 Instead of systemd-networkd

### What we do

The image uses **ifupdown2** (repacked from Proxmox sources with bootc-specific patches) as the network manager, instead of Debian's increasingly default `systemd-networkd`.

### Why it is necessary

1. **Bridge and bond support** — ifupdown2 has mature, well-tested support for Linux bridges (`bridge_ports`), VLANs, and bonding, which `systemd-networkd` handles less gracefully, especially in complex hypervisor or multi-interface setups.
2. **Familiar interface configuration** — The `/etc/network/interfaces` format is familiar to Debian administrators and well-documented. Downstream projects (like DaemonCores-VE) rely on this format for their network topology.
3. **Proxmox ecosystem compatibility** — ifupdown2 is the network manager used by Proxmox VE. Using it in the base image ensures downstream layers do not need to replace the network stack.

### Risks

- ifupdown2 is not the default on modern Debian, which may surprise users expecting `systemd-networkd`.
- The package is repacked from Proxmox sources, introducing a dependency on an external repository.

### Alternative

Use `systemd-networkd` with `.network` units. This would require rewriting all network configuration for downstream layers and losing bridge/bond features that ifupdown2 handles natively.

---

## 5. systemd-timesyncd Repack

### What we do

`systemd-timesyncd` is repacked with a single drop-in that adds `After=network-online.target` and `Wants=network-online.target` to `systemd-timesyncd.service`.

### Why it is necessary

In a bootc environment, `systemd-timesyncd` attempts to reach NTP servers before the network interface is up, causing spurious service failures at boot. The drop-in ensures timesyncd waits for network connectivity before starting.

### Risks

- The repack must be rebuilt whenever the base `systemd-timesyncd` package is updated in Debian.
- A single drop-in is a minimal change, but any repack introduces maintenance overhead.

### Alternative

Use `chrony` instead of `systemd-timesyncd`. Chrony is more robust in offline-first scenarios but is a heavier dependency. For a base image, `systemd-timesyncd` is sufficient and lighter.

---

## 6. Secure Boot MOK Enrollment

### What we do

The `grub-efi-amd64-signed` package includes a `postinst` script that queues MOK (Machine Owner Key) enrollment automatically on package install. On the first reboot after installation, the firmware launches the MokManager screen to enroll the signing key.

### Why it is necessary

UEFI Secure Boot requires every EFI binary in the boot chain to be signed by a trusted key. The standard Debian `shim-signed` package is signed by Microsoft, but GRUB itself is not signed for Secure Boot on custom images. By generating our own signing key, signing GRUB with it, and enrolling it via MOK, we enable Secure Boot on systems that ship with the Microsoft CA in firmware.

### Risks

- The user must manually confirm MOK enrollment on first boot. If they skip it, Secure Boot remains disabled for GRUB.
- The signing key must be kept secure. If the private key (`SB_SIGNING_KEY`) is compromised, an attacker could sign malicious EFI binaries that pass Secure Boot verification.

### Alternative

Disable Secure Boot entirely and rely on TPM or measured boot for integrity. This would work on systems where Secure Boot is not required, but it removes a layer of protection against bootloader-level attacks.

---

## 7. Privileged Container in ISO Workflow

### What we do

The ISO generation job (`DaemonCores-CI/.github/workflows/iso-builder.yml`) runs inside an `almalinux:10` container with `options: --privileged`.

### Why it is necessary

The ISO build process requires `mount -o loop` to extract and repack the Fedora netinstall ISO's squashfs and EFI partitions. In a standard unprivileged container, loop device access is blocked by the kernel's mount namespace restrictions. `--privileged` grants the necessary capabilities (`CAP_SYS_ADMIN`) and device access to perform loop mounts.

### What we do to mitigate the risk

- The privileged container is **isolated to a single dedicated job** (`build-iso`). No other jobs in the pipeline run privileged.
- The job does not process untrusted input. The only external data fetched is:
  - The Fedora netinstall ISO from `archives.fedoraproject.org`
  - The OCI image from GHCR (verified with `cosign verify` before embedding)
  - The `cosign` RPM from GitHub Releases (SHA-256 verified)
- The container image is pinned to `almalinux:10`, not `latest`.
- The job runs on GitHub-hosted `ubuntu-latest` runners, which are ephemeral and destroyed after the job completes.

### Alternative

Run the ISO build on a self-hosted runner with `/dev/loop*` pre-configured and pass `--device /dev/loop0` instead of `--privileged`. This would require maintaining a self-hosted runner infrastructure, which we consider higher overhead than accepting the isolated privileged container for this single job.

---

## 8. Debian Trixie (Testing) as Base

### What we do

debian-bootc is built on Debian 13 (Trixie), which is currently the **testing** distribution, not stable.

### Why testing instead of stable

1. **Kernel recency** — bootc and the underlying ostree/dracut stack require kernel features (e.g., composefs, fs-verity, newer systemd) that are not available or are too old in Debian Stable (Bookworm, 12). Trixie provides a kernel and userspace new enough to satisfy the dependency chain.
2. **bootc/ostree evolution** — The bootc and ostree ecosystems are evolving rapidly. bootc 1.x, composefs integration, and dracut module changes are all landing in Debian testing before they reach stable. Building on stable would mean backporting a significant fraction of the base infrastructure, defeating the purpose of using a standard Debian base.
3. **Future stability** — Debian Trixie will become the next stable release. Tracking testing now means the project will naturally migrate to stable when Trixie is frozen, with minimal disruption.

### Risks

- Testing packages can change without notice. The monthly automated rebuilds (`cron: '0 4 1 * *'`) mitigate this by rebuilding from scratch with the latest testing snapshot.
- Security updates in testing are not as strictly coordinated as in stable. The trade-off is accepted for the features gained.

### Alternative

Wait for Debian 14 (the next stable release) and freeze on it. This would delay the project by 1–2 years. The current approach is to track Trixie and migrate to the next stable release when it is published.

---

## 9. No SHA Pinning for GitHub Actions

### What we do

GitHub Actions in this repository use version tags (e.g., `actions/checkout@v7`, `sigstore/cosign-installer@v3`) instead of pinning to specific commit SHAs.

### Why we use tags instead of SHAs

Pinning actions to commit SHAs provides supply-chain immutability against tag mutation, but shifts the **entire maintenance burden onto the repository owner**: every dependency update requires a manual SHA rotation. In practice this leads to perpetually outdated pins — which provide false security rather than real security.

This repository instead relies on **Dependabot** (`.github/dependabot.yml`) for weekly automated pull requests covering both GitHub Actions and the Docker base image. Updates are reviewed and merged explicitly, providing full auditability without manual tracking overhead. All actions used are from well-established, high-visibility namespaces (`actions/*`, `sigstore/*`, `morph027/*`) where tag mutation would be immediately detected by the community.

### Risks

- A compromised action in a trusted namespace could inject malicious code. Dependabot would surface the update, but a human must review it before merge.
- Tag mutation by a malicious insider at GitHub or a third-party action maintainer is theoretically possible. The namespaces chosen have high community scrutiny.

### Alternative

Pin every action to a SHA and maintain a manual rotation schedule. Rejected because the maintenance overhead is not justified for a project with a single maintainer and monthly rebuild cadence. The Dependabot + review model provides a better trade-off.

---

## 10. `COSIGN_EXPERIMENTAL: 1`

### What we do

The reusable ISO workflow (iso-builder.yml in DaemonCores-CI) sets the environment variable `COSIGN_EXPERIMENTAL=1` before running `cosign verify`.

### Why it is enabled

`COSIGN_EXPERIMENTAL=1` enables experimental features in the cosign CLI. Historically, this flag was required for keyless Sigstore verification workflows (OIDC-based certificate identity verification) before they were promoted to stable in later cosign versions. The project started using cosign when keyless signing was still experimental, and the flag was retained for compatibility with the specific cosign version pinned in the ISO workflow.

The flag may become unnecessary as cosign matures, but its presence is harmless: it simply opts in to features that are stable in newer releases and experimental in older ones.

### Risks

- Experimental features may change behaviour across cosign versions. The cosign version is pinned via the SHA-256 verified RPM download in the ISO workflow, so the behaviour is deterministic within a given build.
- The flag could mask deprecation warnings. Monthly rebuilds surface any CLI changes.

### Alternative

Remove the flag and rely on the stable cosign verification path. This would require verifying that the pinned cosign version supports keyless verification without the flag. Given that the flag is harmless and the version is pinned, we have not prioritized removing it.

---

## Summary Table

| Decision | Justification | Risk Level | Alternative |
|---|---|---|---|
| Default root password | Fallback if firstboot wizard fails | Low (temporary, replaced immediately) | Remove fallback; risk lockout |
| Fedora GRUB fork | BLS (`blscfg`, `blsuki`) modules required by bootc/ostree | Medium (fork divergence from upstream) | Patch Debian GRUB with BLS modules |
| dracut instead of initramfs-tools | Native bootc/ostree module support, `hostonly=no` | Low (well-maintained upstream) | Custom initramfs-tools hooks for ostree |
| ifupdown2 instead of systemd-networkd | Bridge/bond support, Proxmox ecosystem compatibility | Low (repack from audited sources) | systemd-networkd with `.network` units |
| systemd-timesyncd repack | Prevent spurious boot failures by ordering after network-online | Very low (single drop-in) | Use chrony instead |
| Secure Boot MOK enrollment | Enable Secure Boot on standard UEFI firmware with Microsoft CA | Medium (key management burden) | Disable Secure Boot, rely on TPM |
| Privileged ISO container | Required for `mount -o loop` | Low (isolated to single job, ephemeral runner) | Self-hosted runner with loop devices |
| Debian Trixie (testing) | Kernel recency, bootc/ostree evolution, future stability | Medium (testing instability) | Wait for Debian 14 stable |
| No SHA pinning for Actions | Dependabot + review > manual SHA rotation | Low (trusted namespaces) | Pin all SHAs manually |
| `COSIGN_EXPERIMENTAL: 1` | Historical requirement for keyless verification | Very low (pinned cosign version) | Verify stable path and remove |

---

## Related Documents

- [`README.md`](../README.md) — Full project documentation
- [`docs/architecture.md`](architecture.md) — Architecture overview, build pipeline, first-boot flow
- [`Containerfile`](../Containerfile) — Image composition definition
