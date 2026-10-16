# assets/installer/

Branding assets for the **bootc-installer** graphical installer, injected into the
[GResource bundle](https://docs.gtk.org/gio/struct.Resource.html) at build time
(before `meson compile`, in `workflows/bootc-debs-builder/packages.yml`).

## Asset files

| File | Format | Dimensions | GResource path | Role |
|------|--------|-----------|----------------|------|
| `welcome.svg` | SVG source | 512 × 512 | — | Rasterised to `welcome.png` at build time |
| `welcome.png` | PNG | 512 × 512 | `assets/welcome.png` | Installer page header icon (displayed at 128 px) |
| `complete.svg` | SVG | 600 × 300 | `assets/complete.svg` | Installation complete illustration |
| `ready.svg` | SVG | 600 × 300 | `assets/ready.svg` | System ready / reboot illustration |
| `containerized.svg` | SVG | 600 × 300 | `assets/containerized.svg` | bootc / OCI concept illustration |

`welcome.png` is **not committed** — it is generated from `welcome.svg` during
the CI build step using `rsvg-convert` and then injected before `meson compile`.

## Visual identity

All assets share the DaemonCores color palette derived from the existing geometric
triangle theme:

| Token | Hex | Role |
|-------|-----|------|
| `--dcos-blue` | `#446EC5` | Triangle fill, primary |
| `--dcos-vivid` | `#2F6BE8` | Icon strokes, ring |
| `--dcos-cyan` | `#39E2F9` | Triangle accent |
| `--dcos-light` | `#EAF4FD` | Background gradient |
| `--dcos-navy` | `#0E1F4A` | Dark triangles |
| `--debian-red` | `#d70a53` | Debian swirl (welcome icon) |

The **welcome icon** (`welcome.svg`) is a clean SVG recreation of the Debian
swirl: two stroked arcs forming a 315° outer "C" and a 188° inner arc, producing
the classic Debian spiral at any resolution.

The **illustration assets** (`complete.svg`, `ready.svg`, `containerized.svg`)
use a geometric triangle mosaic background (matching `assets/banner/anaconda-sidebar.png`)
with a frosted-glass circle overlay carrying the central icon motif.

## How injection works

`packages.yml` (bootc-installer build section, after `submodule update --init`, before `meson setup`):

```bash
# Rasterise the Debian swirl SVG to PNG (512×512, transparent bg)
rsvg-convert -w 512 -h 512 \
  "${SAVE_PWD}/assets/installer/welcome.svg" \
  -o /build/bootc-installer-src/assets/welcome.png

# Replace upstream illustration assets with DaemonCores versions
cp "${SAVE_PWD}/assets/installer/complete.svg"      /build/bootc-installer-src/assets/complete.svg
cp "${SAVE_PWD}/assets/installer/ready.svg"         /build/bootc-installer-src/assets/ready.svg
cp "${SAVE_PWD}/assets/installer/containerized.svg" /build/bootc-installer-src/assets/containerized.svg
```

Meson then compiles all of these into `bootc-installer.gresource` as usual.

## Upstream reference

- bootc-installer source: `frostyard/bootc-installer` (GTK4/Libadwaita/Python3)
- GResource manifest: `data/bootc-installer.gresource.xml`
- Icon display code: `bootc_installer/pages/_base.py` → `BootcPageHeader`
  sets `pixel-size: 128` on the welcome icon via `page_header.set_from_resource()`
- `distro_logo` in `recipe.json` uses the GResource URI:
  `resource:///org/bootcinstaller/Installer/assets/welcome.png`
