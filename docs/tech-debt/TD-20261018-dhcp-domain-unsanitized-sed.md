---
name: td-20261018-dhcp-domain-unsanitized-sed
description: DHCP-advertised domain is interpolated unescaped into sed programs that rewrite /etc/hosts as root.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Full audit
      note: first detection
    - date: 2026-10-18
      status: Verified in source
      reviewer: Security audit 0.8.2
      note: re-confirmed at cited lines; ID reused, no slug change
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-dhcp-domain-unsanitized-sed

- **Area**: Security
- **Category**: security
- **Severity**: Medium
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`ifupdown2-autoconf` copies the `option domain-name` value from the DHCP probe lease into `/run/ifupdown2-dhcp-domain`, and `domain-set` interpolates it unescaped as the replacement of `sed -i -e "s|{{ FQDN }}|${FQDN}|g"` on `/etc/hosts`, running as root at every `networking.service` start.

## Impact
A DHCP server on the LAN controls part of a root sed program. A domain containing `|` or `&` breaks or alters the substitution. Because `setdomaine || true` swallows the failure, `/etc/hosts` is left as the raw template copy with literal `{{ IP }}` / `{{ HOST }}` lines. GNU sed's `e`/`w` substitution flags are reachable through the same channel. hypothesis: whether ISC dhclient escapes these characters in the lease file decides if this goes beyond breakage to command execution. Confirm before raising the severity.

## Where (pointers)
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf:37-38` — domain copied verbatim from the lease file
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:19` — FQDN read from /run/ifupdown2-dhcp-domain
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:32-36` — unescaped sed replacement on /etc/hosts
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/domain-set:55` — failure swallowed by `|| true`
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/lib/systemd/system/networking.service.d/ifupdown2-autoconf.conf:3` — ExecStartPost hook

## Suggested direction
Validate FQDN against a hostname/domain regex (`^[A-Za-z0-9.-]{1,253}$`) and fall back to `local` otherwise. Render with a non-sed method, or escape `|`, `&` and `\`. Add a `workflows/tests.yml` check that `/etc/hosts` has no `{{` left.

## Resolution (commit c083560)
Added `[[ "${FQDN}" =~ ^[A-Za-z0-9.-]{1,253}$ ]] || FQDN="local"` in `domain-set` before the sed substitution. Values containing `|`, `&`, `\`, or other sed-special characters are rejected and replaced with `"local"`. This makes the guard explicit rather than relying on dhclient escaping behaviour.
