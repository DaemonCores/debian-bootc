---
name: td-20261018-minimal-bootstrap-tools-retained
description: Minimal image installs git/curl/wget/openssl in Phase 1 for bootstrap and never removes them.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Docker audit 0.8.2
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-minimal-bootstrap-tools-retained

- **Area**: Infra
- **Category**: docker
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`Containerfile.minimal` Phase 1 installs `ca-certificates openssl git curl wget`. Only `wget` is used afterwards (fetching the bootc GPG key in Phase 2); `git` and `curl` are never invoked in the file, and none of the three is purged before the image ends. The file header states an ultra-minimal footprint target.

## Impact
`git` (plus its dependencies) and two HTTP clients ship in every minimal OS image and every ostree delta, enlarging size and the CVE surface of the image the minimal flavour is meant to shrink.

## Where (pointers)
- `Containerfile.minimal:2-6` — ultra-minimal target stated
- `Containerfile.minimal:126-132` — Phase 1 install of git/curl/wget
- `Containerfile.minimal:151` — only later use (`wget` for the GPG key)
- `Containerfile.minimal:259-290` — final phases, no purge

## Suggested direction
Drop `git` and `curl` from Phase 1, and `apt purge --autoremove wget` after the key download, or fetch the key with an `ADD --checksum=sha256:...` instruction.

## Next step
`create ticket`

## Resolution
`git` and `curl` are no longer installed in `Containerfile.minimal` (nothing in the file, the shipped scripts or `workflows/tests.yml` uses them), and `wget` is purged with `--autoremove` right after the signing-key download and its `sha256sum -c`. Packages that depend on one of these tools still pull it in. Not yet verified by a real minimal image build.
