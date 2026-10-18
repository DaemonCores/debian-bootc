---
name: td-20261018-domain-set-dead-reset-branch
description: domain-set `resetdomaine` branch is unreachable and writes the whole /etc/hosts content into one entry.
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

# TD-20261018-domain-set-dead-reset-branch

- **Area**: Backend
- **Category**: code-quality
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`lines=$(echo ${HOSTS} | wc -l)` always yields `1`, because unquoted `echo` collapses the file to one line and an empty value prints one newline. So `setdomaine` always runs and `resetdomaine` is dead code. `resetdomaine` would also append `${HOSTS}.${FQDN}`, which is the full previous file content, where `${HOST}` was meant. It also deletes lines with unanchored regexes, so `/${IP}/d` with IP `10.0.0.1` matches `10.0.0.10`.

## Impact
Today: none at runtime, because the branch never runs. The script's own comment (lines 50-51) misstates the behaviour, and anyone who 'fixes' the line-count check would activate the corrupted `/etc/hosts` writer.

## Where (pointers)
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:44-48` — resetdomaine uses ${HOSTS} instead of ${HOST}; unanchored deletes
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:50-58` — line-count check that is always 1

## Suggested direction
Delete `resetdomaine` and the line-count check, and always render from `/etc/hosts.tpl`. Otherwise fix the variable to `${HOST}`, anchor the deletes and quote `"${HOSTS}"`.

## Next step
`create ticket`
