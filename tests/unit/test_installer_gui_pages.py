"""Graphical first-boot setup pages of the bootc-installer GUI.

Every first-boot question (hostname, locale, keyboard, root account, SSH root
policy, user account, NVIDIA EULA) must be asked by native Libadwaita pages of
the vendored GUI (no tty wizard, no dialog outside the flow), and no personal
value may be tracked in the shipped installer recipe.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = (
    ROOT / 'workflows' / 'bootc-debs-builder' / 'bootc-installer-src'
)
RECIPE = (
    ROOT / 'src' / 'buildisopreinstall' / 'etc' / 'bootc-installer' /
    'recipe.json'
)
# Never tolerated in a tracked file of the public repository.
PERSONAL_TOKENS = ('gabriel', 'pikatsuto', 'gmail.com', 'daemonnode')


def _blp(name: str) -> str:
    """Return the blueprint source of one installer page.

    Args:
        name: File name in the ``gtk`` blueprint directory.

    Returns:
        The file content.
    """
    return (INSTALLER / 'gtk' / name).read_text()


def test_system_page_is_adwaita_idiomatic() -> None:
    """The system page uses preference groups and row widgets, not raw GTK."""
    page = _blp('default-system.blp')
    assert 'template $BootcDefaultSystem: Adw.Bin' in page
    assert 'Adw.PreferencesPage' in page
    assert 'Adw.PreferencesGroup locale_group' in page
    assert 'Adw.ComboRow locale_row' in page
    assert 'Adw.ComboRow keyboard_row' in page
    assert 'Adw.EntryRow hostname_entry' in page
    assert 'Adw.PasswordEntryRow root_password_entry' in page
    assert 'Adw.ActionRow' in page
    assert 'Switch ssh_root_switch' in page
    # The labels travel through gettext.
    for title in ('System language', 'Keyboard layout', 'Hostname'):
        assert f'_("{title}' in page


def test_first_boot_steps_are_pages_in_the_flow() -> None:
    """User, system and GPU-security pages exist and ride the recipe steps."""
    builder = (INSTALLER / 'utils' / 'builder.py.patch').read_text()
    for default in (
        'BootcDefaultSystem', 'BootcDefaultUsers', 'BootcDefaultGpuSecurity'
    ):
        assert default in builder
    recipe = json.loads(RECIPE.read_text())
    for step in ('user', 'system', 'gpu_security'):
        assert recipe['steps'][step] == {'template': step}
    gresource = (INSTALLER / 'bootc-installer.gresource.xml.patch').read_text()
    for page in ('default-system.ui', 'default-gpu-security.ui'):
        assert page in gresource

    meson = (INSTALLER / 'meson.build.patch').read_text()
    for blueprint in ('default-system.blp', 'default-gpu-security.blp'):
        assert blueprint in meson

    defaults = (INSTALLER / 'defaults' / 'meson.build.patch').read_text()
    for module in ('system.py', 'gpu_security.py'):
        assert module in defaults


def test_hostname_prompt_and_hosts_derivation_travel() -> None:
    """The page collects the hostname, upstream derives it, fisherman syncs."""
    page = _blp('default-system.blp')
    assert 'hostname_entry' in page
    finals = (INSTALLER / 'defaults' / 'system.py').read_text()
    assert 'finals["hostname"]' in finals
    processor = (INSTALLER / 'utils' / 'processor.py.patch').read_text()
    # The system finals merge into the recipe the processor builds.
    assert 'apply_system(recipe, merged.get("system"))' in processor
    assert 'apply_locale(recipe, merged.get("system"))' in processor
    fisherman = (ROOT / 'workflows' / 'bootc-debs-builder' / 'fisherman-src')
    post = (fisherman / 'fisherman' / 'internal' / 'post' /
            'hosts.go').read_text()
    # The 127.0.1.1 bootstrap line is rewritten from the chosen hostname.
    assert 'func WriteHostsBootstrap(' in post
    assert '127.0.1.1' in post
    main = (fisherman / 'fisherman' / 'cmd' / 'fisherman' /
            'main.go.patch').read_text()
    assert 'WriteHostsBootstrap(activeTargetMount, r.Hostname)' in main
    assert 'WriteSSHRootPolicy(activeTargetMount' in main
    assert 'WriteLocale(activeTargetMount' in main
    assert 'WriteKeyboard(activeTargetMount' in main


def test_nvidia_eula_is_a_graphical_page() -> None:
    """The NVIDIA license consent happens in-page, not on a console."""
    page = _blp('default-gpu-security.blp')
    assert 'eula_group' in page
    assert 'Adw.EntryRow eula_entry' in page
    module = (INSTALLER / 'defaults' / 'gpu_security.py').read_text()
    assert 'eula_text()' in module
    assert 'eula_accepted' in module
    helper = (INSTALLER / 'utils' / 'gpu_config.py').read_text()
    # The consent is recorded through the privileged live-image helper.
    assert 'HELPER' in helper
    assert 'pkexec' in helper


def test_no_personal_value_is_tracked() -> None:
    """The shipped recipe and the GUI source carry no personal data."""
    watched = [RECIPE, *INSTALLER.rglob('*.py'), *INSTALLER.rglob('*.blp')]
    for text_path in watched:
        if '__pycache__' in text_path.parts:
            continue
        haystack = text_path.read_text(errors='replace').lower()
        # The distribution name is DaemonCores; the registry is its own.
        haystack = haystack.replace('daemoncores', '')
        for token in PERSONAL_TOKENS:
            assert token not in haystack, f'{text_path}: {token}'
