# assets/banner/
Optional branding assets applied during CI builds.

## Files

| File                   | Description                                                              | Orientation | Largeur × Hauteur        |
|------------------------|--------------------------------------------------------------------------|-------------|--------------------------|
| `motd`                 | Message de login (texte, copié dans `/etc/motd`)                         | —           | texte libre              |
| `anaconda-sidebar.png` | Fond du panneau gauche de l'installeur Anaconda                          | vertical    | **637 × 508 px**         |
| `anaconda-logo.png`    | Logo overlayé par-dessus le fond de la sidebar                           | vertical    | **70 × 97 px**           |
|                        | Si absent avec sidebar.png présent : effacé automatiquement (transparent)|             |                          |
| `anaconda-topbar.png`  | Barre de navigation du haut (écrans spoke)                               | horizontal  | **636 × 450 px**         |
| `anaconda-header.png`  | Header du hub principal (écran de sélection)                             | horizontal  | **119 × 36 px**          |

Toutes les dimensions sont en **largeur × hauteur** (Fedora 44, variante server).
Tous les fichiers sont optionnels. Les fichiers manquants sont ignorés silencieusement.

## Chemins dans l'installeur Anaconda (Fedora 44)

| Fichier source         | Variante root                        | Variante server/                         |
|------------------------|--------------------------------------|------------------------------------------|
| `anaconda-sidebar.png` | `pixmaps/sidebar-bg.png` 406×767     | `pixmaps/server/sidebar-bg.png` 637×508  |
| `anaconda-logo.png`    | `pixmaps/sidebar-logo.png` 150×69    | `pixmaps/server/sidebar-logo.png` 70×97  |
| `anaconda-topbar.png`  | `pixmaps/topbar-bg.png` 1040×132     | `pixmaps/server/topbar-bg.png` 636×450   |
| `anaconda-header.png`  | `pixmaps/anaconda_header.png` 119×36 | —                                        |

Le **Server netinstall** charge `fedora-server.css` qui référence les fichiers `server/`.
Le script remplace les deux variantes pour couvrir tous les cas.

Si une future version de Fedora déplace ces chemins, mettre à jour `scripts/inject-banners-iso.sh`.