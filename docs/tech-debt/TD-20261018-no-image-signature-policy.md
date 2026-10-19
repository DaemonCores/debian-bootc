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
- **Status**: Blocked (design change needed, see Resolution)
- **Effort**: M
- **Blast radius**: module (3-5 files)

## Problem (fact)
CI signs published images with keyless cosign (`docs/justifications.md:55`). The image overlays (`src/`, `workflows/bootc-debs-builder/*postinstall/`) ship no `/etc/containers/policy.json` and no `/etc/containers/registries.d/*.yaml` with `use-sigstore-attachments` or a `sigstoreSigned` requirement for `ghcr.io/daemoncores`. The `bootc` package postinst enables `bootc-fetch-apply-updates.timer`, and the installer catalog points at `*-autoupdate` tags.

## Impact
An attacker who can push to the GHCR package (leaked token, compromised CI, or the moving `@main` shared workflow, see TD-20261018-reusable-workflow-main-ref) gets a malicious OS image installed and booted as root on every auto-updating host. The signature exists but nothing on the hosts checks it.

## Where (pointers)
- `docs/justifications.md:55` — cosign signing documented
- `workflows/bootc-debs-builder/preinstall/output/bootc/DEBIAN/postinst:6` — auto-update timer enabled
- `src/buildisopreinstall/etc/bootc-installer/recipe.json:4-8` — installs `*-autoupdate` imgrefs
- `src/buildisopreinstall/etc/containers/` — only `containers.conf` / `storage.conf`, no policy

## Suggested direction
Ship a `policy.json` with a `sigstoreSigned` rule (Fulcio issuer + workflow subject) for `ghcr.io/daemoncores/debian-bootc`, plus a `registries.d` entry that enables sigstore attachments. Add a boot test that `bootc upgrade --check` rejects an unsigned tag.

## Next step
`create ticket`

## Resolution
Not shipped. The containers-image `policy.json` `sigstoreSigned` requirement can only match a Fulcio certificate through `fulcio.subjectEmail` (https://raw.githubusercontent.com/containers/image/main/docs/containers-policy.json.5.md). Keyless signing from GitHub Actions produces a certificate whose identity is a workflow URI, not an email, so the current keyless signatures cannot be required by a host policy. A wrong policy would also block every auto-update on installed hosts, and no image was booted here to prove it works.

Options, all needing a decision: (1) sign with a long-lived cosign key held in a repository secret and ship its public key with `keyPath`; (2) keep keyless and verify only in CI; (3) wait for URI-SAN support in containers-image. Option 1 also needs a boot test that `bootc upgrade --check` rejects an unsigned tag before it is enabled.
