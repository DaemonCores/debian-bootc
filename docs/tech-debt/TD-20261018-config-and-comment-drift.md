---
name: td-20261018-config-and-comment-drift
description: config.yml and Containerfile header comments contradict the values and code they describe.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-config-and-comment-drift

- **Area**: Docs
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`config.yml` says `nosign` is the default and `both` is '(future)', but sets `default: both`. The `Containerfile.minimal` header says the kernel is selected via `linux-image-${ARCH}` and lists `linux-image-amd64` / `linux-image-arm64`, while the code installs `linux-image-${KERNEL_VARIANT}-${ARCH}` specifically to avoid Debian's kernel. The main `Containerfile` Phase 4 comment says it 'Mirrors the main Containerfile', a copy-paste from the minimal file.

## Impact
A maintainer reading config.yml expects unsigned modules while CI builds both. A reader of the minimal header may reintroduce `linux-image-amd64`, which the code comments say breaks `bootc lint` with a second modules directory.

## Where (pointers)
- `config.yml:4` — comment: nosign is default
- `config.yml:6` — comment: both is future
- `config.yml:11` — actual `default: both`
- `Containerfile.minimal:11-19` — header names linux-image-${ARCH} / linux-image-amd64
- `Containerfile.minimal:107` — actual ARG KERNEL_VARIANT=stock
- `Containerfile:21-27` — explains why Debian's linux-image-<arch> must NOT be installed
- `Containerfile:170` — 'Mirrors the main Containerfile exactly' inside the main Containerfile

## Suggested direction
Align the config.yml comment with the chosen default, or the value with the comment. Rewrite the minimal header kernel lines to the KERNEL_VARIANT scheme, and change the Containerfile:170 wording to 'Mirrored in Containerfile.minimal'.

## Resolution (commit c083560)
- `config.yml`: comment updated — `nosign` is no longer labelled "default", `both` is now labelled "default".
- `Containerfile.minimal` header: lines 11-19 now name `linux-image-${KERNEL_VARIANT}-amd64` / `linux-image-${KERNEL_VARIANT}-arm64` instead of the bare `linux-image-${ARCH}` form that would install Debian's conflicting kernel.
- `Containerfile:170`: Phase 4 comment changed from "Mirrors the main Containerfile exactly" (inside the main Containerfile) to "Mirrored in Containerfile.minimal".
