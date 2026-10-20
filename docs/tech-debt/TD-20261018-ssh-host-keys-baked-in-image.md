---
name: td-20261018-ssh-host-keys-baked-in-image
description: openssh-server is installed at image build time and no step removes or regenerates /etc/ssh/ssh_host_* keys, so every deployment may share one host key set.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Security audit 0.8.2
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-ssh-host-keys-baked-in-image

- **Area**: Security
- **Category**: security
- **Severity**: High
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`Containerfile` and `Containerfile.minimal` install `openssh-server` during the image build. No Containerfile, overlay, or first-boot script deletes `/etc/ssh/ssh_host_*`, runs `ssh-keygen -A`, or ships a host-key generation unit (`grep -rnE 'ssh_host|ssh-keygen'` over the repo finds nothing). `sshd` is expected to be active on the main image (`workflows/tests.yml:253-260`).

Verified: the cleanup step is missing from the repo. Hypothesis: Debian's `openssh-server` postinst generates host keys when the package is configured, which would put those keys in the published GHCR layer. Confirm with `podman run --rm ghcr.io/daemoncores/debian-bootc:latest-amd64 ls /etc/ssh/` before acting.

## Impact
If the keys are baked in, every machine installed from the same image digest has the same SSH host private key, and anyone can pull it from the public image. An attacker on the network can then impersonate any deployed host or run a MITM attack on SSH sessions (including the root-password logins that `firstboot-user-setup` can enable) without triggering a host-key warning.

## Where (pointers)
- `Containerfile:136` — `openssh-server` installed at build time
- `Containerfile.minimal:186` — `openssh-server` installed at build time
- `Containerfile.minimal:195-199` — cleanup `rm -rf` list, no `/etc/ssh/ssh_host_*`
- `Containerfile:180-189` — ostree migration cleanup, no `/etc/ssh/ssh_host_*`
- `workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:256-262` — configures sshd but never regenerates host keys

## Suggested direction
`rm -f /etc/ssh/ssh_host_*` in the final RUN of each Containerfile, and ship a `ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key` oneshot (`ssh-keygen -A`, `Before=ssh.service`). Add a `workflows/tests.yml` check that host keys exist at boot and differ from the image layer.

## Resolution (commit c083560)
- `rm -f /etc/ssh/ssh_host_*` added at the end of Phase 4 RUN in both `Containerfile` and `Containerfile.minimal`.
- `src/debianpostinstall/etc/systemd/system/ssh-host-keygen.service` and its minimal counterpart created: `ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key`, `ExecStart=/usr/bin/ssh-keygen -A`, `Before=ssh.service`.
- Unit enabled in Phase 4 RUN (`Containerfile`) and Phase 3 RUN (`Containerfile.minimal`).
- Runtime test `SSH host keys regenerated at first boot` added to `workflows/tests.yml`.
