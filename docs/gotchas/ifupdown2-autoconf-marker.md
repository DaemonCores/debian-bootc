# Gotcha: ifupdown2-autoconf requires its marker line in /etc/network/interfaces

## What happened

The custom ifupdown2 package ships a first-boot autoconfiguration script
(`ifupdown2-autoconf`) that runs as `ExecStartPre` of `networking.service`. On startup
it probes for the first ethernet interface via `ip link`, sends a DHCP probe, and writes
the discovered configuration back into `/etc/network/interfaces`.

The script exits immediately if `/etc/network/interfaces` does **not** begin with:

```
# ifupdown2-autoconf: auto-configured on boot, remove this line to disable
```

If the marker is absent, no DHCP probe runs, no interface gets an IP, and the VM
is unreachable for the entire 900-second SSH timeout window in CI boot tests.

## What the default file looks like

```
# ifupdown2-autoconf: auto-configured on boot, remove this line to disable
# interfaces(5) file used by ifup(8) and ifdown(8)

auto lo
iface lo inet loopback
```

The script rewrites the file at boot with the detected interface name and DHCP stanza.

## Rule

The overlay file `src/debianpostinstall/etc/network/interfaces` (copied into the image
in Phase 4 via `COPY ./src/debianpostinstall /`) **must** keep the marker line as its
first line. Do not replace it with static hardcoded interface names — the script handles
interface discovery automatically, which is required for QEMU virtio-net whose interface
names vary across kernel versions.

The runtime test `ifupdown2-autoconf marker present` (variant: main) in
`workflows/tests.yml` guards against regression [src: file: workflows/tests.yml].

## Source

Root cause of the 900-second SSH timeout loop observed in CI runs 39127697200–39161370501.
Fixed in commit db8ce3a.
