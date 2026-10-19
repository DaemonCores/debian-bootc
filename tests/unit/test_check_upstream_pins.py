"""Unit tests for scripts/check_upstream_pins.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_upstream_pins as cup


def test_read_pins_finds_every_manifest_pin() -> None:
    """The real manifest carries all four pins."""
    pins = cup.read_pins(cup.PACKAGES.read_text(encoding="utf-8"))
    assert set(pins) == set(cup.UPSTREAMS)


def test_outdated_ignores_leading_v() -> None:
    """A tag with a ``v`` prefix matches the same bare version."""
    pins = {"OSTREE_VER": "2026.4"}
    assert cup.outdated(pins, lambda _repo: "v2026.4") == []


def test_outdated_reports_newer_release() -> None:
    """A newer upstream tag is reported with both versions."""
    pins = {"BOOTC_VER": "v1.16.2"}
    assert cup.outdated(pins, lambda _repo: "v1.17.1") == [
        ("BOOTC_VER", "v1.16.2", "v1.17.1")
    ]
