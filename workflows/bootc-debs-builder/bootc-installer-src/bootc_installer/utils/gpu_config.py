"""GPU profile and module-signature settings of the installer ``gpu_security`` step.

The GPU usage profile (consumed by ``dc-gpu`` on the installed system) and the
module signature enforcement (the ``module.sig_enforce=1`` kernel argument)
are install-time choices. The NVIDIA license is tied to the image, not to the
hardware: it is required exactly when the selected image is a recipe entry
carrying an ``eula`` key. The gate itself is delegated to the live image
helper ``nvidia-eula-stage``; the helpers here hold no GTK code so they can be
tested alone.
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


def selected_imgref(finals: dict | None, recipe: dict | None) -> str:
    """Name the image the installation will deploy.

    Args:
        finals: Finals of the image selection step, or None when it was not
            shown.
        recipe: Installer recipe, used for its default ``imgref``.

    Returns:
        The custom image if one was typed, else the selected catalog image,
        else the recipe default; empty when none is known.
    """
    finals = finals or {}
    recipe = recipe or {}
    return (
        finals.get("custom_image") or finals.get("selected_image")
        or recipe.get("imgref") or ""
    )


def eula_required(recipe: dict | None, imgref: str) -> bool:
    """Tell whether the NVIDIA license must be accepted for this image.

    Args:
        recipe: Installer recipe holding the ``images`` catalog.
        imgref: Image the installation will deploy.

    Returns:
        True when the catalog entry of ``imgref`` carries an ``eula`` key.
        Images absent from the catalog (custom ones) never require it.
    """
    if not imgref:
        return False
    for entry in (recipe or {}).get("images", []):
        if isinstance(entry, dict) and entry.get("imgref") == imgref:
            return bool(entry.get("eula"))
    return False


def eula_accepted(typed: str) -> bool:
    """Tell whether the typed text is the exact acceptance word.

    Args:
        typed: Text entered by the user.

    Returns:
        True only for ``ACCEPT`` itself, as the helper demands on a console.
    """
    return typed == ACCEPT_WORD


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


def stage_choice(
    usage: str, accepted: bool, imgref: str = "", run: Runner = subprocess.run
) -> bool:
    """Record the choice through the privileged live image helper.

    The helper stays the single gate: it refuses an image whose catalog entry
    requires the license while no acceptance is recorded, whatever the caller
    did.

    Args:
        usage: Chosen GPU usage profile, one of ``USAGES``.
        accepted: Whether the user accepted the NVIDIA EULA.
        imgref: Image the installation will deploy, checked by the helper.
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
    if imgref:
        commands.append(["pkexec", HELPER, "image", imgref])
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
