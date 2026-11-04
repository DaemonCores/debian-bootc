#!/usr/bin/env python3
"""gpu-set-stage - install-time GPU module set selector (P-513a pattern).

Installer-lane helper (wiki: GPU-Support.md, GPU FINAL, owner 2026-11-03).
The GPU module set is an install-time variable like the usage profile and
the NVIDIA EULA acceptance: the image ships NONE of the four sets
(gpu-ia, gpu-gaming, gpu-ia-nvidia, gpu-gaming-nvidia), the installer
records the choice and this helper delivers it to the deployed target.

Commands:

    sets                        print the available set names, one per line
    set <name>                  record the chosen set for the install step
    status                      print the recorded set (empty when none)
    base <ref>                  record the base image reference for derive
    derive <name> [base_ref]    build the derived NVIDIA image of the
                                install (owner 03/11: the bootc-image-
                                builder lane, proven in P-757) through a
                                local compose — base payload, the signed
                                NVIDIA repo and the -nvidia module set
                                deb; prints and records the derived ref
    derived                     print the recorded derived image ref
    install <name> [root]       deliver the set to the target root: the
                                loader policy conf is always copied into
                                <root>/etc/modprobe.d/, and the set deb is
                                pulled from the APT repo when it can be
                                (apt download pinned to the kernel version
                                found in <root>/usr/lib/modules, then
                                dpkg --root=... -i); when the repo is
                                unreachable the conf-only delivery keeps
                                going and says so on stderr. Exits 1 only
                                when even the conf payload is missing.

The set name rides the fisherman recipe (``gpuSet``, written from the
installer GPU step); ``install`` is idempotent and run by fisherman after
the deployment, so a re-run over the same target converges.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

STATE_DIR = Path(os.environ.get("GPU_SET_STATE_DIR", "/run/bootc-installer"))
SET_FILE = STATE_DIR / "gpu-set"
# The conf payloads the live image ships (verbatim copies of the policy
# files the set debs deliver; a unit test pins them against
# workflows/bootc-debs-builder/kernel/modules/gpu/modprobe/).
PAYLOAD_DIR = Path(
    os.environ.get(
        "GPU_SET_PAYLOAD_DIR",
        "/usr/share/debian-bootc/gpu-sets",
    )
)
APT_TIMEOUT = 120
# NVIDIA user-space packages, the exact list of the derived image (the
# signed NVIDIA repo supplies the proprietary user-space at derive time; it
# is never hosted by us).
NVIDIA_PKGS = (
    "firmware-nvidia-gsp",
    "nvidia-driver-libs",
    "libcuda1",
    "nvidia-opencl-icd",
    "nvidia-vulkan-icd",
    "nvidia-smi",
    "nvidia-persistenced",
)
NVIDIA_REPO_BASE = os.environ.get(
    "NVIDIA_REPO_BASE",
    "https://developer.download.nvidia.com/compute/cuda/repos",
)
DERIVE_CMD = os.environ.get(
    "DC_GPU_DERIVE_CMD", ""
)  # overridable compose command, {CONTEXT}/{CONTAINERFILE}/{DERIVED}/{SET}
SETS = (
    "gpu-ia",
    "gpu-gaming",
    "gpu-ia-nvidia",
    "gpu-gaming-nvidia",
)
# The conf file every set deb ships; the -nvidia sets carry their own
# (dc-gpu-<usage>-nvidia.conf), the two open sets the usage one.
CONF_OF = {
    "gpu-ia": "dc-gpu-ia.conf",
    "gpu-gaming": "dc-gpu-gaming.conf",
    "gpu-ia-nvidia": "dc-gpu-ia-nvidia.conf",
    "gpu-gaming-nvidia": "dc-gpu-gaming-nvidia.conf",
}


def fail(message: str) -> NoReturn:
    """Print an error on stderr and exit with status 1.

    Args:
        message: The error text to report.
    """
    print(f"gpu-set-stage: {message}", file=sys.stderr)
    sys.exit(1)


def main_target(root: str | None) -> Path:
    """Resolve the target root of the delivery.

    Args:
        root: Command-line root argument, or None to read INSTALL_ROOT.

    Returns:
        The target root as a Path.
    """
    where = root or os.environ.get("INSTALL_ROOT") or ""
    if not where or not Path(where).is_absolute():
        fail(f"no target root: pass one or set INSTALL_ROOT={where!r}")
    return Path(where)


def conf_path(name: str) -> Path:
    """Return the shipped conf payload of one set.

    Args:
        name: One of ``SETS``.

    Returns:
        The payload path.
    """
    payload = PAYLOAD_DIR / CONF_OF[name]
    if not payload.is_file():
        fail(f"payload {payload} missing")
    return payload


def kver_of(root: Path) -> str:
    """Read the kernel release the target was deployed with.

    Args:
        root: Target root; the modules live in usr/lib/modules/<kver>.

    Returns:
        The single module directory name, empty when ambiguous.
    """
    modules = root / "usr" / "lib" / "modules"
    try:
        versions = sorted(
            p.name for p in modules.iterdir()
            if p.is_dir() and not p.name.startswith("build")
        )
    except OSError:
        return ""
    return versions[0] if len(versions) == 1 else ""


def apt_cache_dir() -> Path:
    """Create and return a scratch directory for the apt downloads.

    Returns:
        The scratch path; falls back to a temporary directory when the
        default location cannot be created (sandboxed runs, read-only /run).
    """
    scratch = Path(os.environ.get("GPU_SET_APT_DIR", "/run/bootc-installer"))
    try:
        (scratch / "apt").mkdir(parents=True, exist_ok=True)
    except OSError:
        scratch = Path(tempfile.gettempdir()) / "gpu-set-apt"
        try:
            (scratch / "apt").mkdir(parents=True, exist_ok=True)
        except OSError:
            return scratch / "apt"  # apt will fail; conf-only delivery stands
    return scratch / "apt"


def download_deb(name: str, kver: str) -> Path | None:
    """Pull one set deb from the APT repo, pinned to the built kernel.

    The set debs are versioned ``<kernel version>-1+r1`` (the KDEB_PKGVERSION
    revision of the kernel build): the exact pin is tried first, the unpinned
    candidate second (reported on stderr) — a mismatched build never installs
    silently, the dpkg Depends of the deb refuses it.

    Args:
        name: The set deb name (a ``SETS`` entry).
        kver: Kernel release the target was deployed with.

    Returns:
        Path of the downloaded deb, or None when no pull can happen.
    """
    if not kver:
        print(
            "gpu-set-stage: no kernel version in the target, "
            "the set deb pin is unknown",
            file=sys.stderr,
        )
        return None
    base = kver.rsplit("-", 1)[0] if "-" in kver else kver
    cache = apt_cache_dir()
    for pin, report in ((f"{name}={base}-1+r1", True), (name, False)):
        done = subprocess.run(
            ["apt-get", "download", pin],
            capture_output=True,
            text=True,
            check=False,
            timeout=APT_TIMEOUT,
            cwd=str(cache),
        )
        got = sorted(cache.glob(f"{name}_*.deb"))
        if got:
            if not report:
                print(
                    f"gpu-set-stage: WARNING unpinned candidate for {name} "
                    f"(kernel {kver})",
                    file=sys.stderr,
                )
            return got[-1]
    print(
        f"gpu-set-stage: no repo candidate for {name} (kernel {kver}): "
        f"{done.stderr.strip().splitlines()[-1:] if done.stderr else ''}",
        file=sys.stderr,
    )
    return None


def copy_conf(name: str, root: Path) -> Path:
    """Copy the loader policy conf of one set into the target.

    Args:
        name: One of ``SETS``.
        root: Target root.

    Returns:
        The conf path inside the target.
    """
    modprobe = root / "etc" / "modprobe.d"
    modprobe.mkdir(parents=True, exist_ok=True)
    target = modprobe / CONF_OF[name]
    shutil.copyfile(conf_path(name), target)
    return target


def cmd_sets() -> int:
    """List the available set names.

    Returns:
        0 always; the names go to stdout.
    """
    for name in SETS:
        print(name)
    return 0


def cmd_set(name: str) -> int:
    """Record the chosen set for the install step.

    Args:
        name: One of ``SETS``.

    Returns:
        0 on success, 1 for an unknown set.
    """
    if name not in SETS:
        fail(f"{name}: unknown GPU set, expected one of {', '.join(SETS)}")
    State().write(name)
    return 0


def cmd_status() -> int:
    """Print the recorded set (empty when none).

    Returns:
        0 always; the recorded name (possibly empty) goes to stdout.
    """
    print(State().read())
    return 0


class State:
    """The state files of this install session."""

    def __init__(self, name: str = "gpu-set") -> None:
        """Point at one named state file (gpu-set, derived-base, ...).

        Args:
            name: State file stem inside the state directory.
        """
        self.file = STATE_DIR / name

    def read(self) -> str:
        """Return the recorded value, empty when nothing was recorded.

        Returns:
            The state file content, stripped.
        """
        try:
            return self.file.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def write(self, value: str) -> None:
        """Record the value in the state directory.

        Args:
            value: The content to record (one line).
        """
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(f"{value}\n", encoding="utf-8")


def _nvidia_containerfile(set_name: str, base: str) -> str:
    """Build the derived-image containerfile of an NVIDIA install.

    The package list is the payload of the decision (owner 03/11): the base
    payload, the SIGNED NVIDIA repository (NVIDIA's documented cuda-keyring
    method; the proprietary binaries are pulled from NVIDIA's repo at build
    time, never hosted by us) and the gpu-*-nvidia module set deb from the
    DaemonCores APT repo (which pulls its sibling open set and the
    linux-modules-nvidia base). The same-release and single-kernel guards
    are enforced verbatim in the generated containerfile.

    Args:
        set_name: A ``SETS`` entry ending with ``-nvidia``.
        base: The base image reference of the install.

    Returns:
        The containerfile text.
    """
    pkgs = " ".join(NVIDIA_PKGS)
    return f"""\
FROM {base}
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
RUN apt-get update \\
    && apt-get install -y --no-install-recommends ca-certificates curl
# The SIGNED NVIDIA repository for this Debian release (cuda-keyring, the
# documented method; same commands as the shipped nvidia-apt-repo helper).
RUN base="{NVIDIA_REPO_BASE}" \\
    && . /etc/os-release \\
    && case "$(dpkg --print-architecture)" in \\
         amd64) nv_arch=x86_64 ;; arm64) nv_arch=sbsa ;; \\
         *) echo "no NVIDIA repository for this architecture" >&2; exit 1 ;; \\
       esac \\
    && work=$(mktemp -d) \\
    && curl -fsSL --retry 3 -o "$work/cuda-keyring.deb" \\
       "$base/$ID$VERSION_ID/$nv_arch/cuda-keyring_1.1-1_all.deb" \\
    && dpkg -i "$work/cuda-keyring.deb" \\
    && rm -rf "$work"
RUN apt-get update \\
    && apt-get install -y --no-install-recommends {pkgs} {set_name} \\
    && module_release=$(dpkg-query -W -f='\\${{Version}}' \\
         linux-modules-nvidia | sed 's/-.*//; s/+.*//') \\
    && userspace_release=$(dpkg-query -W -f='\\${{Version}}' \\
         libcuda1 | sed 's/-.*//') \\
    && {{ [ "$module_release" = "$userspace_release" ] \\
         || {{ echo "NVIDIA module and user-space releases differ" \\
              >&2; exit 1; }}; }} \\
    && {{ [ "$(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d \\
        | wc -l)" -eq 1 ] \\
         || {{ echo "more than one kernel in the derived image" \\
              >&2; exit 1; }}; }}
LABEL org.daemoncores.requires-eula="nvidia"
"""


def _derive_command(
    context: Path, containerfile: Path, derived: str, set_name: str
) -> list[str]:
    """Compose the command that builds the derived image.

    The default is the local podman compose of the install-time derivation
    (podman build — the derived image is a container, the bib ISO flow
    deploys it, both proven in P-757: /tmp/bib-proof). The command can be
    fully overridden through DC_GPU_DERIVE_CMD with the {CONTEXT},
    {CONTAINERFILE}, {DERIVED} and {SET} placeholders.

    Args:
        context: Build context directory.
        containerfile: Path of the generated containerfile.
        derived: Reference of the image to produce.
        set_name: The set name recorded in the image label.

    Returns:
        The argument list.
    """
    if DERIVE_CMD:
        command = DERIVE_CMD.replace("{CONTEXT}", str(context))
        command = command.replace("{CONTAINERFILE}", str(containerfile))
        command = command.replace("{DERIVED}", derived)
        command = command.replace("{SET}", set_name)
        return ["sh", "-c", command]
    return [
        "podman", "build", "-q", "-t", derived, "-f",
        str(containerfile),
        str(context)
    ]


def cmd_derive(set_name: str, base: str | None) -> int:
    """Build the derived NVIDIA image of this install and record its ref.

    Args:
        set_name: One of ``SETS`` with the ``-nvidia`` suffix (the consent
            gate already ran in the installer step before this command).
        base: The base image reference (the installer payload ref).

    Returns:
        0 when the derived image exists and its ref was recorded; 1 when
        the compose failed or the set/open-set mismatch was refused.
    """
    if set_name not in SETS:
        fail(f"{set_name}: unknown GPU set")
    if not set_name.endswith("-nvidia"):
        fail(
            f"{set_name}: only the -nvidia sets are derived images "
            "(the open sets are debs pulled from the APT repo)"
        )
    where = base or State("derived-base").read()
    if not where:
        fail("no base image reference (pass one or record it before)")
    context = apt_cache_dir().parent / "derive" / set_name
    context.mkdir(parents=True, exist_ok=True)
    containerfile = context / "Containerfile"
    containerfile.write_text(
        _nvidia_containerfile(set_name, where), encoding="utf-8"
    )
    derived = f"{where}-nvidia"
    command = _derive_command(context, containerfile, derived, set_name)
    done = subprocess.run(
        command, capture_output=True, text=True, check=False, timeout=3600
    )
    if done.returncode != 0:
        print(done.stdout[-800:] if done.stdout else "", file=sys.stderr)
        print(done.stderr[-800:] if done.stderr else "", file=sys.stderr)
        print(
            f"gpu-set-stage: derive compose failed for {derived}",
            file=sys.stderr
        )
        return 1
    State("derived-imgref").write(derived)
    print(derived)
    return 0


def cmd_install(name: str, root: str | None) -> int:
    """Deliver one set to the target: conf always, deb when reachable.

    Args:
        name: One of ``SETS``.
        root: Target root argument (INSTALL_ROOT honoured otherwise).

    Returns:
        0 when the conf was delivered and the deb install either happened
        or was declined loudly; 1 only when even the conf payload fails.
    """
    if name not in SETS:
        fail(f"{name}: unknown GPU set, expected one of {', '.join(SETS)}")
    where = main_target(root)
    conf = copy_conf(name, where)
    deb = download_deb(name, kver_of(where))
    if deb is not None:
        done = subprocess.run(
            ["dpkg", f"--root={where}", "-i",
             str(deb)],
            capture_output=True,
            text=True,
            check=False,
            timeout=APT_TIMEOUT,
        )
        if done.returncode != 0:
            print(
                f"gpu-set-stage: dpkg refused {deb.name}: "
                f"{done.stderr.strip().splitlines()[-1:]} — "
                "the conf-only delivery stands",
                file=sys.stderr,
            )
            return 0
        print(f"gpu-set-stage: {name} installed from repo with {conf}")
        return 0
    print(
        f"gpu-set-stage: {name} delivered conf-only ({conf}), "
        "deb left to the APT repo on first update"
    )
    return 0


def main() -> NoReturn:
    """Entry point: dispatch the command line."""
    args: list[str] = sys.argv[1:]
    if not args:
        print((__doc__ or "usage").strip(), file=sys.stderr)
        sys.exit(1)
    command, rest = args[0], args[1:]
    if command == "sets" and not rest:
        sys.exit(cmd_sets())
    if command == "set" and len(rest) == 1:
        sys.exit(cmd_set(rest[0]))
    if command == "status" and not rest:
        sys.exit(cmd_status())
    if command == "base" and len(rest) == 1:
        State("derived-base").write(rest[0])
        sys.exit(0)
    if command == "derived" and not rest:
        print(State("derived-imgref").read())
        sys.exit(0)
    if command == "derive" and len(rest) in (1, 2):
        sys.exit(cmd_derive(rest[0], rest[1] if len(rest) == 2 else None))
    if command == "install" and len(rest) in (1, 2):
        sys.exit(cmd_install(rest[0], rest[1] if len(rest) == 2 else None))
    fail(
        "usage: gpu-set-stage {sets|set <name>|status|base <ref>|"
        "derive <name> [base_ref]|derived|install <name> [root]}"
    )


if __name__ == "__main__":
    main()
