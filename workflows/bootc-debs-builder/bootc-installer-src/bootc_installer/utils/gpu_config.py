"""GPU profile and module-signature settings of the installer ``gpu_security`` step.

One image carries the drivers of every GPU vendor and one kernel serves both
signature policies, so both are install-time choices: the GPU usage profile
(consumed by ``dc-gpu`` on the installed system) and the module signature
enforcement (the ``module.sig_enforce=1`` kernel argument). The NVIDIA EULA
gate is delegated to the live image helper ``nvidia-eula-stage``; the helpers
here hold no GTK code so they can be tested alone.
"""

import logging
import subprocess
from collections.abc import Callable

logger = logging.getLogger(__name__)

HELPER = "/usr/libexec/debian-bootc/nvidia-eula-stage"
# Order of the usage rows in the step; the first one is the default.
USAGES = ("auto", "gaming", "ia")
ACCEPT_WORD = "ACCEPT"
COMMAND_TIMEOUT = 60

Runner = Callable[..., subprocess.CompletedProcess]


def eula_required(usage: str, nvidia_present: bool) -> bool:
    """Tell whether the NVIDIA EULA must be accepted for this choice.

    Args:
        usage: Chosen GPU usage profile.
        nvidia_present: Whether an NVIDIA GPU was detected.

    Returns:
        True only for the ``ia`` profile on a machine with an NVIDIA GPU, the
        sole case where the NVIDIA user-space gets activated.
    """
    return usage == "ia" and nvidia_present


def eula_accepted(typed: str) -> bool:
    """Tell whether the typed text is the exact acceptance word.

    Args:
        typed: Text entered by the user.

    Returns:
        True only for ``ACCEPT`` itself, as the helper demands on a console.
    """
    return typed == ACCEPT_WORD


def nvidia_present(run: Runner = subprocess.run) -> bool:
    """Detect an NVIDIA GPU through the live image helper.

    Args:
        run: ``subprocess.run`` compatible callable (replaced in tests).

    Returns:
        True when the helper reports a device; False when none is found or
        the helper cannot run (the EULA gate then does not apply).
    """
    try:
        done = run([HELPER, "probe"], capture_output=True, text=True,
                   check=False, timeout=COMMAND_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as error:
        logger.warning("GPU probe could not run: %s", error)
        return False
    return done.returncode == 0


def eula_text(run: Runner = subprocess.run) -> str:
    """Read the shipped NVIDIA EULA through the live image helper.

    Args:
        run: ``subprocess.run`` compatible callable (replaced in tests).

    Returns:
        The EULA text, empty when the helper cannot provide it.
    """
    try:
        done = run([HELPER, "text"], capture_output=True, text=True,
                   check=False, timeout=COMMAND_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as error:
        logger.warning("EULA text unavailable: %s", error)
        return ""
    return done.stdout if done.returncode == 0 else ""


def stage_choice(usage: str, accepted: bool, run: Runner = subprocess.run) -> bool:
    """Record the choice through the privileged live image helper.

    The helper stays the single gate: it refuses ``ia`` on an NVIDIA machine
    without the acceptance flag, whatever the caller did.

    Args:
        usage: Chosen GPU usage profile, one of ``USAGES``.
        accepted: Whether the user accepted the NVIDIA EULA.
        run: ``subprocess.run`` compatible callable (replaced in tests).

    Returns:
        True when the helper accepted the choice.
    """
    if usage not in USAGES:
        return False
    commands = []
    if accepted:
        commands.append(["pkexec", HELPER, "consent", "--accept"])
    commands.append(["pkexec", HELPER, "usage", usage])
    for command in commands:
        try:
            done = run(command, capture_output=True, text=True, check=False,
                       timeout=COMMAND_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as error:
            logger.warning("GPU choice could not be recorded: %s", error)
            return False
        if done.returncode != 0:
            logger.info("GPU choice refused (exit %s)", done.returncode)
            return False
    return True


def apply_gpu(recipe: dict, gpu: dict | None) -> None:
    """Merge the ``gpu`` step result into a fisherman recipe, in place.

    Args:
        recipe: Fisherman recipe being built.
        gpu: The ``gpu`` entry of the merged finals, or None when the step
            was not shown (the recipe is then left untouched).
    """
    if not gpu:
        return
    usage = gpu.get("usage")
    if usage in USAGES:
        recipe["gpuUsage"] = usage
        recipe["nvidiaConsent"] = bool(gpu.get("nvidiaConsent", False))
    if "sigEnforce" in gpu:
        recipe["sigEnforce"] = bool(gpu["sigEnforce"])
