"""Install-parity of the bootc-installer with the former first-boot wizard.

Every wizard step (user, root password, sudo, ssh policy, hostname, hosts
bootstrap, locale, keyboard) must have an install-side path: a recipe native
fisherman field the bootc-installer system step fills and a fisherman post
helper that applies it on the installed system. One assertion per step; the
wizard itself must be gone.
"""

import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest

from tests.support.documents import (
    load_json,
    load_yaml,
    mapping,
    sequence,
    text,
)
from tests.support.modules import bare_loader, load_module

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "workflows" / "bootc-debs-builder"
MANIFEST = BUILDER / "packages.yml"
RECIPE = (
    ROOT / "src" / "buildisopreinstall" / "etc" / "bootc-installer" /
    "recipe.json"
)
INSTALLER = BUILDER / "bootc_installer"
FISHERMAN = BUILDER / "fisherman-src"
WIZARD_DIR = BUILDER / "firstbootpostinstall"
WIZARD_SCRIPT = (
    ROOT / "workflows" / "bootc-debs-builder" / "firstbootpostinstall" / "usr" /
    "local" / "bin" / "firstboot-user-setup"
)


@runtime_checkable
class _SystemScript(Protocol):
    """Surface of ``system_config.py`` used by the tests."""

    def valid_hostname(self, hostname: str) -> bool:
        """Tell whether a hostname is a valid RFC 1123 label.

        Args:
            hostname: Candidate hostname.

        Returns:
            True when letters, digits and inner hyphens only.
        """
        ...

    def user_groups(self, base: list[str], sudo: bool) -> list[str]:
        """Compute the supplementary groups of the created user.

        Args:
            base: Groups the installer already assigns.
            sudo: Whether the user keeps the admin group.

        Returns:
            The groups to assign, without duplicates.
        """
        ...


@runtime_checkable
class _LocaleScript(Protocol):
    """Surface of ``locale_config.py`` used by the tests."""

    def valid_locale(self, locale: str) -> bool:
        """Tell whether a string is a glibc locale name.

        Args:
            locale: Candidate locale.

        Returns:
            True for the ``language[_TERRITORY].charset`` shape.
        """
        ...

    def valid_keyboard(
        self, layout: str, variant: str, model: str = ...
    ) -> bool:
        """Tell whether the three XKB names are acceptable.

        Args:
            layout: XKB layout.
            variant: XKB variant, empty for the layout default.
            model: XKB model.

        Returns:
            True when every name is an XKB token.
        """
        ...


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


def _system_config() -> _SystemScript:
    """Load ``system_config.py`` from the installer overlay, without GTK.

    Returns:
        The executed module, imported without any GTK dependency.

    Raises:
        TypeError: when the module lacks its test surface.
    """
    module = load_module(
        "system_config", INSTALLER / "utils" / "system_config.py"
    )
    if not isinstance(module, _SystemScript):
        raise TypeError("system_config.py lacks its test surface")
    return module


def _locale_config() -> _LocaleScript:
    """Load ``locale_config.py`` from the installer overlay, without GTK.

    Returns:
        The executed module, imported without any GTK dependency.

    Raises:
        TypeError: when the module lacks its test surface.
    """
    module = load_module(
        "locale_config", INSTALLER / "utils" / "locale_config.py"
    )
    if not isinstance(module, _LocaleScript):
        raise TypeError("locale_config.py lacks its test surface")
    return module


def test_user_account_created_by_the_recipe() -> None:
    """The user step writes the account; fisherman keeps the creation call."""
    recipe = mapping(load_json(RECIPE.read_text()))
    assert mapping(recipe["steps"])["user"] == {"template": "user"}
    fisherman = _overlay_text(FISHERMAN)
    assert 'r.User.Username != ""' in fisherman


def test_root_password_set_by_the_installer() -> None:
    """The system step validates and travels, fisherman applies chpasswd."""
    installer = _overlay_text(INSTALLER)
    assert 'recipe["rootPassword"]' in installer
    assert (
        "8 characters" in installer or "len &gt;= 8" in installer or (
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
    processor = (INSTALLER / "utils" / "processor.py.patch").read_text()
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
    installer = (INSTALLER / "utils" / "builder.py.patch").read_text()
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
    data = mapping(load_yaml(MANIFEST.read_text()))
    assert all(
        text(mapping(entry)["name"]) != "firstboot-user-setup"
        for entry in sequence(data["packages"])
    )
    assert not WIZARD_DIR.exists()
    assert not WIZARD_SCRIPT.is_file()
    assert (ROOT / "Makefile").read_text().find("firstboot-user-setup") == -1
    assert (ROOT /
            "Containerfile").read_text().find("firstboot-user-setup") == -1


def test_system_loader_guard_rejects_a_module_without_the_surface(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The system loader refuses a module that lacks the tested helpers.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(sys.modules[__name__], 'load_module', bare_loader)
    with pytest.raises(TypeError, match='lacks its test surface'):
        _ = _system_config()


def test_locale_loader_guard_rejects_a_module_without_the_surface(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The locale loader refuses a module that lacks the tested helpers.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(sys.modules[__name__], 'load_module', bare_loader)
    with pytest.raises(TypeError, match='lacks its test surface'):
        _ = _locale_config()
