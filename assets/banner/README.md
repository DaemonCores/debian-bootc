# assets/banner/ — legacy (Anaconda / Fedora)

> **These assets are no longer used.**
> The ISO pipeline was rewritten to use `bootc-image-builder` with
> `bootc-installer` (GTK4). See `assets/installer/` for the current
> branding assets and injection documentation.

The files below were originally injected into the **Anaconda** installer
(Fedora-based ISOs). They are kept as historical reference for the visual
style (the blue geometric triangle pattern from `anaconda-sidebar.png`
is reproduced as clean SVG in `assets/installer/`).

## Original files

| File | Description | Dimensions |
|------|-------------|-----------|
| `anaconda-sidebar.png` | Left panel background (blue triangles) | 637 × 508 px |
| `anaconda-logo.png` | Sidebar logo (Debian swirl + text) | 70 × 97 px |
| `anaconda-topbar.png` | Top navigation bar | 636 × 450 px |
| `anaconda-header.png` | Main hub header | 119 × 36 px |
| `flat-overrides.css` | GTK CSS color overrides | — |

## Color palette (extracted from `anaconda-sidebar.png`)

These tokens carry over to the new bootc-installer theme in `assets/installer/`:

```css
@define-color flat_primary       #446EC5;
@define-color flat_primary_dark  #2F6BE8;
@define-color flat_accent        #39E2F9;
@define-color flat_bg            #EAF4FD;
@define-color flat_text          #0E1F4A;
```
