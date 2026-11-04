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
GPU_SET_HELPER = "/usr/libexec/debian-bootc/gpu-set-stage"
# Order of the usage rows in the step; the first one is the default.
USAGES = ("auto", "gaming", "ia")
# The GPU module sets of the installed kernel (GPU FINAL, owner
# 2026-11-03): the usage profile resolves the open set, the nvidia toggle
# selects the -nvidia variant. ``auto`` resolves to gaming before the set
# selection: the set debs are install-time-only, auto cannot be revisited
# by dc-gpu at boot.
GPU_SETS = ("gpu-ia", "gpu-gaming", "gpu-ia-nvidia", "gpu-gaming-nvidia")
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


def selected_set(usage: str, nvidia: bool) -> str:
    """Resolve the GPU module set of an install-time choice.

    Args:
        usage: Chosen GPU usage profile (``auto`` resolves to ``gaming``:
            the set debs are an install-time choice, the open set carries
            the display build the live session and a later `dc-gpu set`
            can both use; the compute build is opt-in).
        nvidia: Whether the NVIDIA modules/stack were selected.

    Returns:
        One of ``GPU_SETS``.
    """
    open_set = "gaming" if usage == "auto" else usage
    return f"gpu-{open_set}-nvidia" if nvidia else f"gpu-{open_set}"


def stage_choice(
    usage: str,
    accepted: bool,
    imgref: str = "",
    nvidia: bool = False,
    run: Runner = subprocess.run,
) -> bool:
    """Record the choice through the privileged live image helpers.

    The helper stays the single gate: it refuses an image whose catalog entry
    requires the license while no acceptance is recorded, whatever the caller
    did. The GPU module set is recorded right after the usage, so the
    install step delivers exactly the set of the recorded profile.

    Args:
        usage: Chosen GPU usage profile, one of ``USAGES``.
        accepted: Whether the user accepted the NVIDIA EULA.
        imgref: Image the installation will deploy, checked by the helper.
        nvidia: Whether the NVIDIA modules/stack were selected.
        run: ``subprocess.run`` compatible callable (replaced in tests).

    Returns:
        True when the helpers accepted the choice.
    """
    if usage not in USAGES:
        return False
    commands = []
    if accepted:
        commands.append(["pkexec", HELPER, "consent", "--accept"])
    commands.append(["pkexec", HELPER, "usage", usage])
    if imgref:
        commands.append(["pkexec", HELPER, "image", imgref])
    commands.append(["pkexec", GPU_SET_HELPER, "set", selected_set(usage, nvidia)])
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
        nvidia = bool(gpu.get("nvidiaConsent", False)) or bool(
            gpu.get("nvidia", False)
        )
        recipe["gpuUsage"] = usage
        recipe["nvidiaConsent"] = bool(gpu.get("nvidiaConsent", False))
        # The module set of the install (GPU FINAL): the fisherman post step
        # delivers it (recipe key consumed by WriteGPUModuleSet).
        recipe["gpuSet"] = selected_set(usage, nvidia)
    if "sigEnforce" in gpu:
        recipe["sigEnforce"] = bool(gpu["sigEnforce"])
