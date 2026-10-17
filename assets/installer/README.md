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

All assets are transparent, use the Debian carmine accent, and draw as line
icons rather than filled shapes.

| Token | Hex | Role |
|-------|-----|------|
| carmine | `#d70a53` | Icon strokes, title, rule — the Debian accent |
| body | `#7b7d85` | Description text |

The **welcome icon** (`welcome.svg`) is an SVG recreation of the Debian swirl:
two stroked arcs forming a 315° outer "C" and a 188° inner arc, at any resolution.

The **illustration assets** (`complete.svg`, `ready.svg`, `containerized.svg`)
each carry a Lucide line icon (`circle-check`, `power`, `layers`), a title
underlined in carmine, and a one-line description.

## Text colour is fixed, not themed

The installer draws these illustrations through `Gtk.Picture`, which rasterises
the SVG with librsvg at load time. That path never receives the widget theme, so
a single SVG cannot render black text on a light theme and white text on a dark
one — `@media (prefers-color-scheme: dark)` and `currentColor` both resolve to
nothing there. The two text colours are therefore chosen to stay legible on
either ground:

| Element | Colour | On white | On `#1e1e1e` |
|---------|--------|----------|--------------|
| Title (bold) | `#d70a53` | 5.2:1 | 3.2:1 |
| Description | `#7b7d85` | 4.1:1 | 4.1:1 |

`#7b7d85` is the neutral with the highest minimum contrast across both grounds;
no single colour scores better. A true per-theme split would need two files per
illustration selected by the installer at runtime.

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

The image catalog is taken from the same `recipe.json` the live image ships at
`/etc/bootc-installer/recipe.json` (the first path `RecipeLoader` checks) and is
bundled as `fisherman/data/images.json` so the fallback catalog matches it.

Meson then compiles all of these into `bootc-installer.gresource` as usual.

## Upstream reference

- bootc-installer source: `frostyard/bootc-installer` (GTK4/Libadwaita/Python3)
- GResource manifest: `bootc_installer/bootc-installer.gresource.xml`
- Icon display code: `bootc_installer/widgets/page_header.py` → `BootcPageHeader`
  sets `pixel-size: 128` on the welcome icon via `page_header.set_from_resource()`
- Tour illustrations: `bootc_installer/views/tour.py` → `Gtk.Picture.set_resource()`
- `distro_logo` in `recipe.json` uses the GResource URI:
  `resource:///org/bootcinstaller/Installer/assets/welcome.png`
