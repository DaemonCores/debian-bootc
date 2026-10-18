---
name: td-20261018-iso-cache-order-recipe-before-apt
description: `Containerfile.iso` copies `Containerfile*` and the recipe generator before the apt install layer, so any Containerfile edit busts the installer-stack cache.
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

# TD-20261018-iso-cache-order-recipe-before-apt

- **Area**: Infra
- **Category**: docker
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
In `Containerfile.iso`, `COPY Containerfile* /tmp/recipe-gen/` and `COPY ./scripts/gen-recipe.py` (plus the generator `RUN`) come before the `apt install` of the installer stack (fisherman, bootc-installer, cage, mesa, NetworkManager, GTK/GNOME libs). The apt layer does not depend on the recipe output.

## Impact
Editing any `Containerfile*` or `scripts/gen-recipe.py` invalidates the cached apt layer, forcing a full re-download/install of the installer stack on every ISO build that follows a variant edit.

## Where (pointers)
- `Containerfile.iso:56-64` — recipe-gen COPY + RUN
- `Containerfile.iso:65-82` — apt install of the installer stack

## Suggested direction
Move the `RUN apt update && apt install ...` block above the `COPY Containerfile*` / `gen-recipe.py` steps (keep `COPY ./src/buildisopreinstall /` first only if the apt sources it ships are needed by the install).

## Next step
`create ticket`

## Resolution
The recipe generation (`COPY Containerfile*`, `COPY gen-recipe.py`, generator `RUN`) now follows the installer-stack `apt install` in `Containerfile.iso`, so editing a Containerfile or the generator no longer invalidates the apt layer. `COPY ./src/buildisopreinstall /` stays first. Not yet verified by a real ISO build.
