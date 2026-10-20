---
name: td-20261018-containerfile-phase-duplication
description: Containerfile and Containerfile.minimal duplicate the SSL, APT-trust and ostree-migration phases by hand.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Code-quality audit
      note: re-confirmed by focused code-quality audit
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-containerfile-phase-duplication

- **Area**: Infra
- **Category**: code-quality
- **Severity**: Low
- **Status**: Mitigated (ostree layout shared; phases 1 and 2 still duplicated)
- **Effort**: M
- **Blast radius**: local (1-2 files)

## Problem (fact)
Phase 1 (SSL prerequisites), Phase 2 (bootc APT key with `BOOTC_GPG_SHA256`) and the ostree filesystem migration are copy-pasted between the two Containerfiles. A comment asks maintainers to keep the layout identical.

## Impact
Key rotation or a layout fix must be applied twice, and `docs/AGENTS.md` already lists forgetting the second file as a common mistake. A missed sync produces an image that builds but fails at `bootc install` or upgrade.

## Where (pointers)
- `Containerfile:43` — BOOTC_GPG_SHA256
- `Containerfile.minimal:115` — duplicate BOOTC_GPG_SHA256
- `Containerfile:172-199` — ostree migration
- `Containerfile.minimal:261-285` — duplicate ostree migration
- `Containerfile.minimal:259` — 'Mirrors the main Containerfile exactly; do NOT change'

## Suggested direction
Move the shared phases into a script shipped in an overlay (e.g. `/usr/libexec/debian-bootc/ostree-layout`) or a shared build stage, and call it from both files.

## Next step
`create ticket`

## Resolution
The ostree filesystem migration now lives in `src/ostreelayout/usr/libexec/debian-bootc/ostree-layout`, copied and run by `Containerfile` and `Containerfile.minimal`. It is covered by shellcheck and shfmt (POSIX) in `make check`. Not executed: it rewrites `/home`, `/root` and `/usr/lib/locale`, so only the CI build and boot test can exercise it. Phase 1 (SSL prerequisites) and Phase 2 (bootc APT key) remain duplicated: the minimal image installs fewer tools, so they are not identical, and sharing them needs a build stage rather than a script.
