"""Install-parity of the bootc-installer with the former first-boot wizard.

Every wizard step (user, root password, sudo, ssh policy, hostname, hosts
bootstrap, locale, keyboard) must have an install-side path: a recipe native
fisherman field the bootc-installer system step fills and a fisherman post
helper that applies it on the installed system. One assertion per step; the
wizard itself must be gone.
"""

import json
import types
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "workflows" / "bootc-debs-builder"
MANIFEST = BUILDER / "packages.yml"
RECIPE = (
    ROOT / "src" / "buildisopreinstall" / "etc" / "bootc-installer" /
    "recipe.json"
)
INSTALLER = BUILDER / "bootc-installer-src"
FISHERMAN = BUILDER / "fisherman-src"
WIZARD_DIR = BUILDER / "firstbootpostinstall"
WIZARD_SCRIPT = (
    ROOT / "workflows" / "bootc-debs-builder" / "firstbootpostinstall" / "usr" /
    "local" / "bin" / "firstboot-user-setup"
)


def _overlay_text(overlay: Path) -> str:
    """Return the concatenated text of one source overlay.

    Args:
        overlay: Overlay directory.

    Returns:
        Every patch and added file of the overlay, joined.
    """
    return "\n".join(
        f.read_text() for f in sorted(overlay.rglob("*"))
        if f.is_file() and "__pycache__" not in f.parts
    )


def _system_config() -> types.ModuleType:
    """Load ``system_config.py`` from the installer overlay, without GTK.

    Returns:
        The module, executed without any GTK dependency.
    """
    module = types.ModuleType("system_config")
    exec(
        compile(
            (INSTALLER  / "utils" /
             "system_config.py").read_text(),
            "system_config.py",
            "exec",
        ),
        module.__dict__,
    )
    return module


def _locale_config() -> types.ModuleType:
    """Load ``locale_config.py`` from the installer overlay, without GTK.

    Returns:
        The module, executed without any GTK dependency.
    """
    module = types.ModuleType("locale_config")
    exec(
        compile(
            (INSTALLER  / "utils" /
             "locale_config.py").read_text(),
            "locale_config.py",
            "exec",
        ),
        module.__dict__,
    )
    return module


def _entry(name: str) -> dict[str, Any]:
    """Return one ``packages.yml`` entry.

    Args:
        name: Package name.

    Returns:
        The manifest entry.
    """
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))
    return next(p for p in data["packages"] if p["name"] == name)


def test_user_account_created_by_the_recipe() -> None:
    """The user step writes the account; fisherman keeps the creation call."""
    recipe = json.loads(RECIPE.read_text())
    assert recipe["steps"]["user"] == {"template": "user"}
    fisherman = _overlay_text(FISHERMAN)
    assert 'r.User.Username != ""' in fisherman


def test_root_password_set_by_the_installer() -> None:
    """The system step validates and travels, fisherman applies chpasswd."""
    installer = _overlay_text(INSTALLER)
    assert 'recipe["rootPassword"]' in installer
    assert (
        "8 characters" in installer or "len >= 8" in installer or (
            # valid_root_password is the concrete gate of the step
            "valid_root_password" in installer
        )
    )
    fisherman = _overlay_text(FISHERMAN)
    assert "post.SetRootPassword(activeTargetMount" in fisherman


def test_sudo_rides_the_recipe_groups() -> None:
    """The sudo switch edits user groups; fisherman applies u.Groups."""
    m = _system_config()
    assert "sudo" not in m.user_groups([], False)
    assert "sudo" in m.user_groups([], True)
    processor = (
        INSTALLER  / "utils" / "processor.py.patch"
    ).read_text()
    assert '"groups": user_groups' in processor


def test_ssh_policy_written_as_drop_in() -> None:
    """PermitRootLogin lands in an sshd drop-in, not in interactive config."""
    fisherman = _overlay_text(FISHERMAN)
    assert "01-permitrootlogin.conf" in fisherman
    assert "post.WriteSSHRootPolicy(activeTargetMount" in fisherman
    installer = _overlay_text(INSTALLER)
    assert 'recipe["sshRootLogin"]' in installer


def test_hostname_validated_and_wired() -> None:
    """RFC 1123 validation in the step, WriteHostname in fisherman."""
    m = _system_config()
    assert m.valid_hostname("my-node")
    assert not m.valid_hostname("-bad/")
    fisherman = _overlay_text(FISHERMAN)
    # The recipe field is native (hostname carried by WriteHostname upstream);
    # the installer-side wiring is the hosts bootstrap it derives (test below).
    assert 'json:"hostname"' in fisherman


def test_hosts_bootstrap_follows_the_hostname() -> None:
    """WriteHostsBootstrap replaces the 127.0.1.1 line the wizard refreshed."""
    overlay = _overlay_text(FISHERMAN)
    assert "func WriteHostsBootstrap(" in overlay
    assert "127.0.1.1" in overlay
    main = (FISHERMAN / "fisherman" / "cmd" / "fisherman" /
            "main.go.patch").read_text()
    assert "post.WriteHostsBootstrap(activeTargetMount, r.Hostname)" in main
    tests_manifest = (ROOT / "workflows" / "tests.yml").read_text()
    assert "firstboot wizard removed" in tests_manifest


def test_locale_written_to_the_deployment() -> None:
    """The system step offers locales; fisherman writes /etc/default/locale."""
    m = _locale_config()
    assert m.valid_locale("fr_FR.UTF-8")
    assert not m.valid_locale("not a locale")
    fisherman = _overlay_text(FISHERMAN)
    assert "post.WriteLocale(activeTargetMount" in fisherman
    installer = (INSTALLER  / "utils" /
                 "builder.py.patch").read_text()
    assert "BootcDefaultSystem" in installer


def test_keyboard_written_to_the_deployment() -> None:
    """XKB names validated in the step, /etc/default/keyboard by fisherman."""
    m = _locale_config()
    assert m.valid_keyboard("fr", "oss", "pc105")
    assert not m.valid_keyboard("fr;", "", "pc105")
    fisherman = _overlay_text(FISHERMAN)
    assert "post.WriteKeyboard(activeTargetMount" in fisherman
    assert "DefaultKeyboardModel" in fisherman


def test_no_wizard_remnant_is_shipped() -> None:
    """The deb entry and its sources are gone from every build file."""
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text()))
    assert all(p["name"] != "firstboot-user-setup" for p in data["packages"])
    assert not WIZARD_DIR.exists()
    assert not WIZARD_SCRIPT.is_file()
    assert (ROOT / "Makefile").read_text().find("firstboot-user-setup") == -1
    assert (ROOT /
            "Containerfile").read_text().find("firstboot-user-setup") == -1
