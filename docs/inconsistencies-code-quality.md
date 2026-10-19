# Code-quality inconsistencies

Focused code-quality audit, 2026-10-18. Scope: shell scripts (`workflows/bootc-debs-builder/**/usr/*bin/*`, `bootc-finalize`), inline `build:` scripts in `workflows/bootc-debs-builder/packages.yml`, the three Containerfiles, and `scripts/gen-recipe.py`. The repo has no templates, CSS or web assets. Findings that match existing TDs reuse their IDs, with an `audit_history` entry appended.

| ID | Problem | Area | Severity |
|---|---|---|---|
| [TD-20261018-kernel-modules-bootstrap-duplication](tech-debt/TD-20261018-kernel-modules-bootstrap-duplication.md) | About 70-line kernel-source bootstrap copy-pasted in 3 linux-modules-* builds, already drifting (`packages.yml:261-336`, `:539-614`, `:762-828`) | Backend | Medium |
| [TD-20261018-containerfile-phase-duplication](tech-debt/TD-20261018-containerfile-phase-duplication.md) | SSL/APT-key/ostree phases hand-synced between Containerfiles (`Containerfile.minimal:262`) | Infra | Low |
| [TD-20261018-swallowed-errors-ostree-migration](tech-debt/TD-20261018-swallowed-errors-ostree-migration.md) | `&& cp … \|\| true &&` swallows mkdir failures (`Containerfile:179`, `Containerfile.minimal:271`) | Infra | Low |
| [TD-20261018-grub-efi-entries-duplicated-pins](tech-debt/TD-20261018-grub-efi-entries-duplicated-pins.md) | GRUB version/branch/commit pins and build steps duplicated in amd64/arm64 entries (`packages.yml:1101-977`, `:1149-1151`) | Backend | Low |
| [TD-20261018-grub-efi-arm64-unconsumed](tech-debt/TD-20261018-grub-efi-arm64-unconsumed.md) | grub-efi-arm64-signed built and signed, but nothing in the repo installs it (Inferred) (`packages.yml:1269`) | Backend | Low |
| [TD-20261018-firstboot-duplicated-prompt-logic](tech-debt/TD-20261018-firstboot-duplicated-prompt-logic.md) | Password loop duplicated, and the display-name pipeline duplicated and diverged (`firstboot-user-setup:59-67` vs `:149-150`) | Backend | Low |
| [TD-20261018-domain-set-dead-reset-branch](tech-debt/TD-20261018-domain-set-dead-reset-branch.md) | Unreachable, buggy `resetdomaine` branch (`domain-set:44-58`) | Backend | Low |
| [TD-20261018-orphan-polkit-rule-copy](tech-debt/TD-20261018-orphan-polkit-rule-copy.md) | Byte-identical dead polkit rule under `/etc/rules.d/` | Other | Low |

## Checklist results

- **Templates / markup**: N/A. The repo has no HTML or templating engine. `hosts.tpl` and `issue.tpl` are `sed` placeholder files.
- **Styles**: N/A. The repo has no CSS or SCSS.
- **God files**: verified clean for imperative code. The largest scripts are `firstboot-user-setup` (267 lines), `bootc-finalize` (105) and `gen-recipe.py` (67). `packages.yml` (1713 lines) is a per-package declarative manifest. Its size is a symptom of the duplicated build bodies above, not of mixed responsibilities.
- **Dead code**: `resetdomaine` (existing TD), the orphan polkit rule (existing TD) and `grub-efi-arm64-signed` (Inferred, new TD).
- **Swallowed errors**: `|| true` in the ostree migration (existing TD) and on the kernel purge chain (folded into the kernel bootstrap TD). Other `|| true` uses were sampled and are deliberate and commented, for example `firstboot-user-setup:124-130` and `ifupdown2-autoconf:13`, `:52`.
- **Copy-paste logic**: three findings above (kernel bootstrap, GRUB entries, firstboot prompts), plus the existing Containerfile phase duplication.
- **Typing hygiene**: `scripts/gen-recipe.py` has one function with a `-> None` return annotation and a bare `list` annotation at `:34`. This is negligible for a 67-line script and verified clean. The shell scripts use `set -euo pipefail` and Google-style function headers.
- **TODO/FIXME/HACK**: 0 in source (grep over Containerfiles, `workflows/`, `scripts/`, `src/`, `kernel/`, `kernel/modules/` and `.github/`). Verified clean.
- **Assets**: the 4 SVGs in `assets/installer/` are vector files. No raster images over 300 KB. Verified clean.
- **Requests in loops / memoization**: N/A. The repo has no request path. The only loops are `for grp …` with `getent`/`usermod` in `firstboot-user-setup:249-253`, which run once at first boot.
