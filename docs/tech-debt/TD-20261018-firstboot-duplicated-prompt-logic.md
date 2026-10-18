---
name: td-20261018-firstboot-duplicated-prompt-logic
description: firstboot-user-setup duplicates its password prompt loop and its hostname→display-name pipeline; the two display-name copies already diverge.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Code-quality audit
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-firstboot-duplicated-prompt-logic

- **Area**: Backend
- **Category**: code-quality
- **Severity**: Low
- **Status**: Confirmed by user
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
The user-password and root-password loops are the same apart from their prompt strings (minimum length 8, confirm, mismatch message). The hostname → title-case display name pipeline also appears twice. The first copy maps `-` and `_` to spaces and squeezes repeated spaces. The second maps only `-` and does not squeeze.

## Impact
A change to the password policy, such as a new minimum length, has to be made twice. The wizard title is rendered differently before and after the hostname step for hostnames that contain `_`.

## Where (pointers)
- `workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:176-185` — user password loop
- `workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:189-198` — root password loop
- `workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:59-67` — display name, first copy
- `workflows/bootc-debs-builder/firstbootpostinstall/usr/local/bin/firstboot-user-setup:149-150` — display name, diverged copy

## Suggested direction
Add `_ask_password <label>` and `_display_name <host>` helpers next to the existing `_input`/`_pass` helpers.

## Next step
`create ticket`
