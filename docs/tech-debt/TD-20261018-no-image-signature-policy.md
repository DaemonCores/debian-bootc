---
name: td-20261018-no-image-signature-policy
description: Images are cosign-signed in CI, but deployed hosts ship no containers policy requiring that signature, and the auto-update timer applies whatever the registry serves.
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

# TD-20261018-no-image-signature-policy

- **Area**: Security
- **Category**: security
- **Severity**: Medium
- **Status**: Mitigated (per-repository key and host policy implemented; never run on GitHub, no booted host check)
- **Effort**: M
- **Blast radius**: module (3-5 files)

## Problem (fact)
CI signs published images with keyless cosign (`docs/justifications.md:55`). The image overlays (`src/`, `workflows/bootc-debs-builder/*postinstall/`) ship no `/etc/containers/policy.json` and no `/etc/containers/registries.d/*.yaml` with `use-sigstore-attachments` or a `sigstoreSigned` requirement for `ghcr.io/daemoncores`. The `bootc` package postinst enables `bootc-fetch-apply-updates.timer`, and the installer catalog points at the `latest_<arch>` tags.

## Impact
An attacker who can push to the GHCR package (leaked token, compromised CI, or the moving `@main` shared workflow, see TD-20261018-reusable-workflow-main-ref) gets a malicious OS image installed and booted as root on every auto-updating host. The signature exists but nothing on the hosts checks it.

## Where (pointers)
- `docs/justifications.md:55` — cosign signing documented
- `workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/postinst:6` — auto-update timer enabled
- `src/buildisopreinstall/etc/bootc-installer/recipe.json:4-8` — installs `_<arch>` imgrefs
- `src/buildisopreinstall/etc/containers/` — only `containers.conf` / `storage.conf`, no policy

## Suggested direction
Ship a `policy.json` with a `sigstoreSigned` rule (Fulcio issuer + workflow subject) for `ghcr.io/daemoncores/debian-bootc`, plus a `registries.d` entry that enables sigstore attachments. Add a boot test that `bootc upgrade --check` rejects an unsigned tag.

## Next step
`create ticket`

## Resolution
Option 1 was taken. Keyless signatures cannot be required by a host (containers-image `sigstoreSigned` matches a Fulcio certificate only by e-mail, https://raw.githubusercontent.com/containers/image/main/docs/containers-policy.json.5.md), so each repository now owns a cosign key pair stored as repository secrets (`COSIGN_PRIVATE_KEY`, `COSIGN_PASSWORD`, `COSIGN_PUBLIC_KEY`) while the pipeline stays in DaemonCores-CI:

- The `prepare` stage (DaemonCores-CI, `ensure-secrets.sh`) generates the pair on the first run when `PAT_SECRETS` is set, then restarts the pipeline because secrets created mid-run are only visible to the next run. Without `PAT_SECRETS` the images stay keyless and no policy is shipped.
- `sign-image` signs per-arch images and manifest lists with the key (cosign 2.x, `.sig` attachments). The list step used to sign the first per-arch manifest; it now signs the digest of the list itself.
- `src/debianpostinstall/usr/libexec/debian-bootc/install-signature-policy` writes the public key, a `policy.json` requiring `sigstoreSigned` for the image repository (default stays accept-anything) and a `registries.d` entry with `use-sigstore-attachments: true`; it ships nothing when the public key is empty.

Still unverified: a pipeline run on GitHub, that `bootc upgrade` on a booted host accepts a signed tag and rejects an unsigned one (the boot test the original direction asked for is not written), and that containers-image reads the cosign 2.x signatures as configured. Rotating the key locks hosts that pinned the old public key out of updates; the README tells existing users about the change.
