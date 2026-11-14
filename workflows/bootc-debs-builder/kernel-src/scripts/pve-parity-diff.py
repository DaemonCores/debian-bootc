#!/usr/bin/env python3
"""Regenerate the PVE parity fragment from a stock Proxmox kernel config.

Owner rule (14/11): the kernel config must be audited against the REAL
Debian + Proxmox sources, never a hand-picked subset. This script compares a
stock `config-<pve-version>` file (the reference) with the config a build
produced, and emits every option Proxmox ships as =y/=m that the build lacks.

Usage:
    ./pve-parity-diff.py /boot/config-7.0.14-28-pve \
        /usr/lib/linux-kernel-build-ia-x64v3/config \
        > kernel-src/kconfig/pve/pve-parity.cfg
"""
import re
import sys


def parse(path: str) -> dict:
    """Return {CONFIG_X: value} with explicit 'n' for '# X is not set'."""
    values = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            m = re.match(r"# (CONFIG_\w+) is not set", line)
            if m:
                values[m.group(1)] = "n"
                continue
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                values[key] = val
    return values


def main() -> int:
    """Emit the parity fragment on stdout."""
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    reference, built = parse(sys.argv[1]), parse(sys.argv[2])
    missing = sorted(
        (key, val)
        for key, val in reference.items()
        if val in ("y", "m") and built.get(key) in (None, "n")
    )
    print("# PVE PARITY FRAGMENT — GENERATED, do not hand-edit.")
    print(f"# reference: {sys.argv[1]}")
    print(f"# built    : {sys.argv[2]}")
    print("# Every option Proxmox ships as =y/=m that the build lacked."
          " olddefconfig drops")
    print("# options renamed or removed in the newer tree, so the fragment stays")
    print("# safe across minor versions.")
    print()
    for key, val in missing:
        print(f"{key}={val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
