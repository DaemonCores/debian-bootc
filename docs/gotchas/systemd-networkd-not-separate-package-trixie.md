# Gotcha: systemd-networkd is not a separate apt package on Debian Trixie

## What happened

`apt install systemd-networkd` fails with "Unable to locate package systemd-networkd" on
Debian Trixie. The binary `/lib/systemd/systemd-networkd` ships inside the base `systemd`
package — there is no separate deb for it in either the Debian or the custom bootc APT
repositories used by this project.

## Rule

Do **not** add `systemd-networkd` to any `apt install` list in any Containerfile.
The binary is already present through the `systemd` dependency that every image pulls.

To enable it, use `systemctl enable systemd-networkd.service` in the build RUN — the unit
files are also part of `systemd`. See `Containerfile.minimal` Phase 3 for the canonical
pattern [src: file: Containerfile.minimal:232].

## Source

Confirmed by build failure in CI run 39161370501 (commit db8ce3a / e9ff026).
The `Containerfile.minimal` header already documented this at line 24
("shipped by systemd, not a separate package on Trixie") but the constraint was
violated in commit e9ff026 and fixed in commit 4d9bc98.
