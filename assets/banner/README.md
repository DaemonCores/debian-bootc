# assets/banner/

Optional branding assets applied during CI builds to the Anaconda installer ISO.

## Files

| File                   | Description                                                       | Orientation | Width × Height       |
|------------------------|-------------------------------------------------------------------|-------------|----------------------|
| `motd`                 | Login message (plain text, copied to `/etc/motd`)                 | —           | free text            |
| `anaconda-sidebar.png` | Left panel background in the Anaconda installer                   | vertical    | **637 × 508 px**     |
| `anaconda-logo.png`    | Logo overlaid on top of the sidebar background                    | vertical    | **70 × 97 px**       |
|                        | If absent while sidebar.png is present: auto-cleared (transparent)|             |                      |
| `anaconda-topbar.png`  | Top navigation bar (spoke screens)                                | horizontal  | **636 × 450 px**     |
| `anaconda-header.png`  | Main hub header (selection screen)                                | horizontal  | **119 × 36 px**      |

All dimensions are **width × height** (Fedora 44, server variant).
All files are optional. Missing files are silently skipped.

## Paths inside the Anaconda installer (Fedora 44)

| Source file            | Root variant                         | Server variant                           |
|------------------------|--------------------------------------|------------------------------------------|
| `anaconda-sidebar.png` | `pixmaps/sidebar-bg.png` 406×767     | `pixmaps/server/sidebar-bg.png` 637×508  |
| `anaconda-logo.png`    | `pixmaps/sidebar-logo.png` 150×69    | `pixmaps/server/sidebar-logo.png` 70×97  |
| `anaconda-topbar.png`  | `pixmaps/topbar-bg.png` 1040×132     | `pixmaps/server/topbar-bg.png` 636×450   |
| `anaconda-header.png`  | `pixmaps/anaconda_header.png` 119×36 | —                                        |

The **Server netinstall** loads `fedora-server.css` which references the `server/` variants.
The injection script replaces both variants to cover all cases regardless of which
product CSS Anaconda loads.

If a future Fedora release moves these paths, update `scripts/inject-iso.sh` accordingly.