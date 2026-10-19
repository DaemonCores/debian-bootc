#!/usr/bin/env python3
"""check_upstream_pins.py — report boot-stack pins that are behind upstream.

Usage:
    python3 scripts/check_upstream_pins.py [--strict]

Reads the ``*_VER`` pins of the bootc, bootupd, ostree and composefs build
blocks in ``workflows/bootc-debs-builder/packages.yml`` and compares each with
the latest GitHub release of its upstream repository.  Outdated pins are
printed, one per line.  Nothing is bumped: a bump needs a build (and, for
bootupd, a rebase of the dpkg patch), so it stays a human decision.
With ``--strict`` the exit status is 1 when a pin is outdated (used by the
scheduled workflow); otherwise the report is informational.
"""

import json
import re
import sys
import urllib.request
from collections.abc import Callable
from http.client import HTTPResponse
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "workflows" / "bootc-debs-builder" / "packages.yml"
UPSTREAMS = {
    "BOOTC_VER": "bootc-dev/bootc",
    "BOOTUPD_VER": "coreos/bootupd",
    "COMPOSEFS_VER": "composefs/composefs",
    "OSTREE_VER": "ostreedev/ostree",
}


def read_pins(text: str) -> dict[str, str]:
    """Extract the pinned upstream versions from the manifest.

    Args:
        text: Content of ``packages.yml``.

    Returns:
        Mapping of pin name to its pinned version string.
    """
    pins: dict[str, str] = {}
    for name in UPSTREAMS:
        found = re.search(rf'^\s*{name}:\s*"([^"]+)"', text, re.MULTILINE)
        if found:
            pins[name] = found.group(1)
    return pins


def normalize(version: str) -> str:
    """Strip a leading ``v`` so ``v2026.4`` and ``2026.4`` compare equal.

    Args:
        version: Version or tag string.

    Returns:
        The version without its leading ``v``.
    """
    return version.removeprefix("v")


def fetch_latest(repo: str) -> str:
    """Return the tag of the latest GitHub release of ``repo``.

    Args:
        repo: ``owner/name`` GitHub repository.

    Returns:
        The ``tag_name`` of the latest release.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json"}
    )
    # The URL is built above from a fixed https scheme.
    reply = cast(
        HTTPResponse,
        urllib.request.urlopen(request, timeout=30)  # nosec B310
    )
    with reply as response:
        body = response.read()
    release = cast(dict[str, object], json.loads(body))
    return str(release["tag_name"])


def outdated(pins: dict[str, str],
             fetch: Callable[[str], str]) -> list[tuple[str, str, str]]:
    """List the pins that differ from the latest upstream release.

    Args:
        pins: Mapping of pin name to pinned version.
        fetch: Callable returning the latest release tag of a repository.

    Returns:
        Tuples of (pin name, pinned version, latest tag), in pin order.
    """
    behind: list[tuple[str, str, str]] = []
    for name, pinned in pins.items():
        latest = fetch(UPSTREAMS[name])
        if normalize(latest) != normalize(pinned):
            behind.append((name, pinned, latest))
    return behind


def main(argv: list[str]) -> int:
    """Print the outdated pins and return the exit status.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        1 when ``--strict`` is given and a pin is outdated, else 0.
    """
    behind = outdated(
        read_pins(PACKAGES.read_text(encoding="utf-8")), fetch_latest
    )
    for name, pinned, latest in behind:
        print(f"{name}: pinned {pinned}, upstream {latest}")
    if not behind:
        print("All upstream pins are current.")
    return 1 if behind and "--strict" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
