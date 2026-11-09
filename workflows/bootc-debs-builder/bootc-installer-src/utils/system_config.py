"""System settings collected by the installer ``system`` step.

These are the settings the first-boot setup service used to ask for: the
hostname, the root password, the sudo right of the created user and the sshd
root login policy. The helpers hold no GTK code so they can be tested alone.
"""

import re

HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
MIN_PASSWORD_LENGTH = 8

# Groups every created user joins; fisherman drops those the image lacks.
DEBIAN_USER_GROUPS = (
    "adm", "systemd-journal", "cdrom", "audio", "video", "plugdev", "netdev",
)
ADMIN_GROUP = "sudo"


def valid_hostname(hostname: str) -> bool:
    """Tell whether a hostname is a valid RFC 1123 label (1 to 63 chars).

    Args:
        hostname: Candidate hostname.

    Returns:
        True when letters, digits and inner hyphens only.
    """
    return bool(HOSTNAME_RE.match(hostname))


def valid_root_password(password: str, confirmation: str) -> bool:
    """Tell whether the root password is long enough and confirmed.

    Args:
        password: First entry.
        confirmation: Second entry.

    Returns:
        True when both match and reach the minimum length.
    """
    return len(password) >= MIN_PASSWORD_LENGTH and password == confirmation


def user_groups(base: list, sudo: bool) -> list:
    """Compute the supplementary groups of the created user.

    Args:
        base: Groups the installer already assigns.
        sudo: Whether the user keeps the admin group.

    Returns:
        The base groups without the admin group unless wanted, plus the
        standard Debian groups, without duplicates and in a stable order.
    """
    groups = [g for g in base if g != ADMIN_GROUP]
    groups += [g for g in DEBIAN_USER_GROUPS if g not in groups]
    if sudo:
        groups.insert(0, ADMIN_GROUP)
    return groups


def apply_system(recipe: dict, system: dict | None) -> None:
    """Merge the ``system`` step result into a fisherman recipe, in place.

    Args:
        recipe: Fisherman recipe being built.
        system: The ``system`` entry of the merged finals, or None when the
            step was not shown (the recipe is then left untouched).
    """
    if not system:
        return
    if system.get("rootPassword"):
        recipe["rootPassword"] = system["rootPassword"]
    if "sshRootLogin" in system:
        recipe["sshRootLogin"] = bool(system["sshRootLogin"])
    user = recipe.get("user")
    if user and user.get("username"):
        user["groups"] = user_groups(user.get("groups", []),
                                     bool(system.get("sudo", True)))
