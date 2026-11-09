"""Stage the distribution Secure Boot certificate for MOK enrollment.

The installed system boots through shim, which only trusts the DaemonCores
signing certificate once it is enrolled in the firmware MOK list. The request
is queued from the live session, right after a successful install, by a
privileged helper shipped with the live image; MokManager then asks for the
one-time password on the next boot.
"""

import logging
import os
import secrets
import string
import subprocess

logger = logging.getLogger(__name__)

HELPER = "/usr/libexec/debian-bootc/mok-stage"
PASSWORD_LENGTH = 16


def generate_password() -> str:
    """Generate a random one-time MokManager password.

    Returns:
        A string of 16 random ASCII letters and digits.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(PASSWORD_LENGTH))


def stage_mok_enrollment() -> str:
    """Queue the MOK enrollment through the privileged live-image helper.

    The password is passed on stdin and is never logged.

    Returns:
        The one-time password when an enrollment was queued, otherwise an
        empty string (no helper, no UEFI, key already enrolled, or failure).
    """
    if not os.path.exists(HELPER):
        return ""
    password = generate_password()
    try:
        done = subprocess.run(
            ["pkexec", HELPER],
            input=password,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        logger.warning("MOK enrollment helper could not run: %s", error)
        return ""
    if done.returncode != 0:
        logger.info("MOK enrollment not staged (exit %s)", done.returncode)
        return ""
    return password
