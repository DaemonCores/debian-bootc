#!/usr/bin/env python3
"""Diff a reference kernel config (Debian or Proxmox) against a built one.

Emits the fragment lines for every option the reference ships as =y/=m that
the build lacks. Owner 14/11: the kernel config must be audited against the
REAL sources (Debian linux-config, Proxmox config-<pve>), never a subset.
"""
import collections
import re
import sys

FAMILIES = {
    "LXC/ns": r"NAMESPACES|USER_NS|CGROUP|SECCOMP|PID_NS|NET_NS",
    "netfilter": r"NETFILTER|NF_|CONNTRACK|VETH|BRIDGE|TUN|NAT",
    "fuse/fs": r"FUSE|OVERLAY|EXT4|BTRFS|XFS|NFS|9P|VFAT|ISO9660",
    "DRM/GPU": r"DRM|AMDGPU|I915|FB_|BACKLIGHT",
    "KVM/VFIO": r"KVM|VFIO|VHOST",
    "crypto": r"CRYPTO|DM_CRYPT",
    "blk": r"BLK_|SCSI|ATA|NVME|MD|DM_",
    "sound": r"SND",
    "net-drivers": r"E1000|IGB|IGC|R8169|MLX|VIRTIO_NET|WLAN|WIRELESS",
    "usb": r"USB",
    "acpi": r"ACPI|THERMAL|HWMON|X86_PLATFORM",
}


def parse(path: str) -> dict:
    """{CONFIG_X: value}, 'n' for explicit not-set lines."""
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
    """Print the audit summary and write the fragment next to the reference."""
    reference, built, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    ref, our = parse(reference), parse(built)
    missing = sorted(
        (k, v) for k, v in ref.items() if v in ("y", "m") and our.get(k) in (None, "n")
    )
    active = sum(1 for v in ref.values() if v in ("y", "m"))
    print(f"reference {reference}: {active} active options")
    print(f"missing in {built}: {len(missing)}")
    counts = collections.Counter()
    for key, _ in missing:
        for fam, pat in FAMILIES.items():
            if re.search(pat, key):
                counts[fam] += 1
                break
        else:
            counts["autre"] += 1
    for fam, count in counts.most_common():
        print(f"  {fam}: {count}")
    with open(out_path, "w", encoding="utf-8") as fh:
        for key, val in missing:
            fh.write(f"{key}={val}\n")
    print(f"wrote {out_path} ({len(missing)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
