---
name: td-20261018-orphan-polkit-rule-copy
description: ISO overlay ships a duplicate polkit rule under /etc/rules.d/, a path polkit does not read.
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

# TD-20261018-orphan-polkit-rule-copy

- **Area**: Other
- **Category**: code-quality
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`src/buildisopreinstall/etc/rules.d/50-bootc-installer-live.rules` is byte-identical to `src/buildisopreinstall/etc/polkit-1/rules.d/50-bootc-installer-live.rules`. Only the latter sits in a polkit rules directory.

## Impact
Dead file in the live image. A future edit to only one copy creates confusion about which rule grants the `live` user password-less `org.tunaos.Installer`, a security-relevant rule.

## Where (pointers)
- `src/buildisopreinstall/etc/rules.d/50-bootc-installer-live.rules:1-6` — orphan copy
- `src/buildisopreinstall/etc/polkit-1/rules.d/50-bootc-installer-live.rules:1-6` — effective rule

## Suggested direction
Delete `src/buildisopreinstall/etc/rules.d/`.

## Next step
`create ticket`
