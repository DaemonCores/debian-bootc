"""System settings collected by the installer ``system`` step.

These are the settings the first-boot setup service used to ask for: the
hostname, the root password, the sudo right of the created user and the sshd
root login policy. The helpers hold no GTK code so they can be tested alone.
"""

import re
from collections.abc import Mapping
from typing import TypeGuard

HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
MIN_PASSWORD_LENGTH = 8

# Groups every created user joins; fisherman drops those the image lacks.
DEBIAN_USER_GROUPS = (
    "adm",
    "systemd-journal",
    "cdrom",
    "audio",
    "video",
    "plugdev",
    "netdev",
)
ADMIN_GROUP = "sudo"


def _is_object_dict(value: object) -> TypeGuard[dict[str, object]]:
    """Tell whether a value is a mutable string-keyed dictionary.

    Args:
        value: Candidate value.

    Returns:
        True when the value is a dict.
    """
    return isinstance(value, dict)


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    """Tell whether a value is a list of arbitrary entries.

    Args:
        value: Candidate value.

    Returns:
        True when the value is a list.
    """
    return isinstance(value, list)


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


def user_groups(base: list[str], sudo: bool) -> list[str]:
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


def apply_system(
    recipe: dict[str, object],
    system: Mapping[str, object] | None,
) -> None:
    """Merge the ``system`` step result into a fisherman recipe, in place.

    Args:
        recipe: Fisherman recipe being built.
        system: The ``system`` entry of the merged finals, or None when the
            step was not shown (the recipe is then left untouched).
    """
    if not system:
        return
    password = system.get("rootPassword")
    if isinstance(password, str) and password:
        recipe["rootPassword"] = password
    if "sshRootLogin" in system:
        recipe["sshRootLogin"] = bool(system["sshRootLogin"])
    user = recipe.get("user")
    if not _is_object_dict(user):
        return
    username = user.get("username")
    if not isinstance(username, str) or not username:
        return
    groups_value = user.get("groups")
    base: list[str] = ([g for g in groups_value if isinstance(g, str)]
                       if _is_object_list(groups_value) else [])
    user["groups"] = user_groups(base, bool(system.get("sudo", True)))
