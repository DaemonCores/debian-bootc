---
name: td-20261018-hardcoded-public-dns
description: ifupdown2 autoconf forces Cloudflare and Google public DNS resolvers on every auto-configured host.
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

# TD-20261018-hardcoded-public-dns

- **Area**: Other
- **Severity**: Medium
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
The generated `/etc/network/interfaces` always adds `dns-nameservers 1.1.1.1 8.8.8.8` to the DHCPv4 stanza and `2606:4700:4700::1111 2001:4860:4860::8888` to the DHCPv6 stanza, in addition to whatever the DHCP server provides.

## Impact
Hosts send DNS queries to third-party US resolvers by default, which is a data-transfer and GDPR question for EU deployments. It can also break split-horizon or internal-only DNS on corporate/Proxmox networks and leak internal hostnames. Nothing in the image documents or exposes a switch for this.

## Where (pointers)
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf:29-30` — IPv4 public resolvers
- `workflows/bootc-debs-builder/ifupdown2postinstall/usr/sbin/ifupdown2-autoconf:49-50` — IPv6 public resolvers

## Suggested direction
Use only DHCP-provided resolvers, falling back to public ones only when DHCP supplies none. Alternatively make the fallback list configurable and document it.

## Next step
`create ticket`
