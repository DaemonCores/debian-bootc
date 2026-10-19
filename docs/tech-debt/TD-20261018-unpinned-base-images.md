---
name: td-20261018-unpinned-base-images
description: Image builds use moving base tags (`debian:trixie`, `:latest-<arch>-autoupdate`) without a digest.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Docker audit 0.8.2
      note: re-confirmed by Docker audit 0.8.2 at Containerfile:5, Containerfile.minimal:68, Containerfile.iso:28; ID reused
    - date: 2026-10-18
      status: Accepted decision
      reviewer: Kronn audit validation card
      note: "Accepted as an intentional decision and recorded in docs/decisions.md."
---

# TD-20261018-unpinned-base-images

- **Area**: Infra
- **Category**: docker
- **Severity**: Low
- **Status**: Accepted decision
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`Containerfile` and `Containerfile.minimal` start `FROM debian:trixie`, and `Containerfile.iso` starts `FROM ghcr.io/daemoncores/debian-bootc:latest-${ARCH}-autoupdate`. None are digest-pinned. For `debian:trixie` this is a documented choice to receive security updates automatically.

## Impact
Two builds of the same commit can produce different images. A regression in the upstream base, or in the freshly published base for the ISO, cannot be bisected to a commit. The QEMU tests in `workflows/tests.yml` are the only guard.

## Where (pointers)
- `Containerfile:3-5` — `FROM debian:trixie`, comment states intentional
- `Containerfile.minimal:68` — `FROM debian:trixie`
- `Containerfile.iso:28` — `FROM ...:latest-${ARCH}-autoupdate`
- `docs/justifications.md:9` — trade-off recorded
- `.github/dependabot.yml` — docker ecosystem configured (could bump digests)

## Suggested direction
Either record this as an accepted decision, or pin `debian:trixie@sha256:...` and let the weekly Dependabot docker update bump the digest. For the ISO, pass the exact base digest produced earlier in the same pipeline run as a build-arg.

## Next step
`create ticket`
