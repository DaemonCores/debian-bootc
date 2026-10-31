#####################################################################################
# Standard image, built on Containerfile.base (Debian trixie, not pinned for auto
# security update, with the SSL prerequisites and the trusted bootc APT repository).
# The CI builds the base once per job and passes it as BASE_IMAGE; it never pushes it.
#####################################################################################
ARG BASE_IMAGE=localhost/debian-bootc-base
FROM ${BASE_IMAGE}
# The shell is inherited from the base; repeated so the linter and the reader see it.
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

LABEL org.opencontainers.image.title="Debian Trixie bootc"
LABEL org.opencontainers.image.description="Debian 13 Trixie bootable bootc/ostree container image, signed with cosign."
# Asks the CI for two arm64 kernels (docs/Handoff-Decisions.md, "Two arm64 kernels"): the
# plain tag is built on the 16 KB kernel, and a second arm64-only image tagged
# `<tag>-4k` carries the 4 KB kernel for Raspberry Pi 3 and 4.
LABEL org.daemoncores.arm64-4k-image="true"
# Asks the CI (both signing mode) for the unsigned-kernel twin of this image,
# tagged `<tag>-nosign`: the same image on the -nosign kernel package, for amd64
# and the plain-tag arm64 kernel only. The 4 KB image has no twin.
LABEL org.daemoncores.unsigned-kernel-image="true"


# -----------------------------------------------------------------------------
# Phase 3: Install the package set, kernel excluded (arch-conditional via ARG)
# -----------------------------------------------------------------------------
# The kernel is NOT in this list: it is installed by the next RUN, so the signed image
# and its -nosign twin share every layer up to here.
# The standard image adds the same per-arch driver modules (linux-modules-*, see the
# block after this RUN) so its hardware support does not shrink. Debian's own
# linux-image-${ARCH} is not installed: a second /usr/lib/modules/<kver>/ fails bootc lint.
# linux-headers is NOT installed: it was never published to the custom apt repo
# and Debian's linux-headers-${ARCH} would create a spurious /usr/lib/modules/<kver>/build.
# Recommends are NOT installed (--no-install-recommends): they pulled a mail
# server (exim4), cron, buildah, criu and ~100 other packages into the image.
# The trailing block of the list below keeps, on purpose, the recommends the OS
# needs: bootc install tools (parted dosfstools fdisk), rootless podman
# (uidmap passt aardvark-dns nftables catatonit containers-storage
# fuse-overlayfs), dracut (cryptsetup systemd-cryptsetup kpartx mdadm zstd),
# hardware firmware (firmware-* pulled by firmware-linux-free/misc-nonfree),
# console and ssh usability (console-common ncurses-term psmisc
# linux-sysctl-defaults libpam-wtmpdb), and the login and console stack the last
# booting image carried (systemd-sysv libpam-systemd dbus-user-session kbd
# keyboard-configuration). Derived with apt-get -s for both
# architectures, see docs/tech-debt/TD-20261018-full-image-install-recommends.md.
# The architecture specific recommends are installed in the per-arch block at
# the end of this RUN: x86 GPU firmware on amd64; efibootmgr and the U-Boot
# tooling (libubootenv-tool, device-tree-compiler) on arm64.
# Target architecture: amd64 (x86_64) default; CI overrides to arm64 via --build-arg ARCH=arm64.
ARG ARCH=amd64
# Boot profile, set by the CI from `LABEL org.daemoncores.boot-profile` (generic when
# absent): `generic` boots through UEFI with the Fedora GRUB, `embedded` is arm64
# boards whose firmware loads U-Boot. The CI derives BOOT_PKG and APT_HOLD_PKG from it.
ARG BOOT_PROFILE=generic
# Boot stack chosen by the CI from the architecture and the boot profile:
# grub-efi-amd64-signed (amd64), grub-efi-arm64-signed (arm64 generic) or
# u-boot-tools (arm64 embedded). A separate ARG because arm64 does NOT follow the
# grub-efi-${ARCH} pattern in the embedded profile.
ARG BOOT_PKG=grub-efi-amd64-signed
# Firmware packages: x86_64 includes microcode + full firmware; arm64 drops microcode.
ARG FIRMWARE_PKGS="intel-microcode amd64-microcode firmware-linux-free firmware-linux firmware-misc-nonfree"
# Package(s) to hold from auto-upgrade: the GRUB package of the profile; empty for
# the arm64 embedded profile (no GRUB).
ARG APT_HOLD_PKG=grub-efi-amd64-signed
# Fingerprint of the custom APT repository content for this architecture, kernels and
# device modules excluded (see KERNEL_DEBS_HASH), set by the CI.
# Declared before the first layer installing from it: a changed value re-runs those
# layers, so a rebuilt package is picked up even when its version string is unchanged.
ARG DEBS_HASH=none
RUN apt update \
    && apt install -y --no-install-recommends \
        git \
        curl \
        ${FIRMWARE_PKGS} \
        bootc \
        skopeo \
        podman \
        adduser \
        sudo \
        locales \
        console-setup \
        console-data \
        bash-completion \
        less \
        man-db \
        nano \
        iproute2 \
        groff-base \
        manpages \
        libnss-systemd \
        systemd-timesyncd \
        util-linux-extra \
        btrfs-progs \
        file \
        traceroute \
        lsof \
        bzip2 \
        xz-utils \
        apt-listchanges \
        bind9-host \
        bind9-dnsutils \
        perl \
        wtmpdb \
        media-types \
        liblockfile-bin \
        openssh-server \
        openssh-client \
        reportbug \
        debian-faq \
        krb5-locales \
        inetutils-telnet \
        netcat-traditional \
        doc-debian \
        dbus \
        ifupdown2 \
        openresolv \
        isc-dhcp-client \
        wpasupplicant \
        firstboot-user-setup \
        ${BOOT_PKG} \
        parted \
        dosfstools \
        fdisk \
        uidmap \
        passt \
        aardvark-dns \
        nftables \
        catatonit \
        containers-storage \
        fuse-overlayfs \
        cryptsetup \
        systemd-cryptsetup \
        kpartx \
        mdadm \
        zstd \
        firmware-ath9k-htc \
        firmware-carl9170 \
        firmware-mediatek \
        console-common \
        ncurses-term \
        psmisc \
        linux-sysctl-defaults \
        libpam-wtmpdb \
        systemd-sysv \
        libpam-systemd \
        dbus-user-session \
        kbd \
        keyboard-configuration \
    && { [ -z "${APT_HOLD_PKG}" ] || apt-mark hold "${APT_HOLD_PKG}"; } \
    && apt update \
    && if [ "${ARCH}" = "amd64" ]; then \
        apt install -y --no-install-recommends \
            firmware-intel-graphics \
            firmware-intel-misc \
            firmware-nvidia-graphics; \
    else \
        apt install -y --no-install-recommends \
            efibootmgr \
            libubootenv-tool \
            device-tree-compiler; \
    fi \
    && if [ "${BOOT_PROFILE}" = generic ]; then \
        apt update \
        && apt install -y --no-install-recommends bootupd; \
    fi

# -----------------------------------------------------------------------------
# Phase 4: ostree filesystem migration
# -----------------------------------------------------------------------------
# bootc/ostree requires /home, /root, /mnt, /srv, /opt as symlinks into /var so the
# read-only /usr tree can be swapped atomically while mutable state persists in /var.
# The scripts shared with Containerfile.minimal ship in src/basepostinstall.
COPY ./src/debianpostinstall /
COPY ./src/basepostinstall /
RUN /usr/libexec/debian-bootc/ostree-layout \
    && rm -f /etc/ssh/ssh_host_*

#####################################################################################
# GPU stack — every open vendor stack, both usages
#####################################################################################
# Placed BEFORE the kernel layer: the user-space does not depend on the kernel,
# so the signed and -nosign images share this layer.
# The image carries the open drivers of EVERY vendor (AMD, Intel, NVIDIA via
# nouveau) for the display (gaming) and compute (ia) usages. What differs
# between the usages is the BUILD of the open stack, not its content: the plan debs
# gpu-userspace-<profile>-<level> are Mesa compiled in CI from source with every
# Gallium/Vulkan driver, once per profile (gaming, ia) and per CPU level
# (x64v1 baseline, x64v2/x64v3 as glibc-hwcaps libraries that ld.so prefers on a
# CPU supporting them; generic on arm64). Each profile lives under its own
# /usr/lib/dc-gpu/<profile> prefix, inert until `dc-gpu` activates it; the
# profile is chosen at install by the bootc-installer and changed later with
# `dc-gpu set gaming|ia|auto` (GPU-VARIANTS.md). Kernel side: the in-tree
# drivers (amdgpu, nouveau, i915/xe) are =m, so nothing compiles on the target.
# The NVIDIA proprietary stack (user-space and the plan deb linux-modules-nvidia)
# is binary-only and license-gated: it ships in its own image,
# Containerfile.nvidia, built FROM this one.
# Installed from Debian instead (not recompilable here):
#   common   Vulkan loader, glvnd dispatch libraries, vulkan/VA-API/OpenCL
#            tools, non-free firmware
#   AMD      graphics firmware, ROCm OpenCL/HIP runtime and tools (no source
#            build of ROCm yet)
#   Intel    graphics firmware, VA-API media driver, Level Zero loader (no
#            source build of the compute runtime yet)
# The loader of each stack (Vulkan/OpenCL ICDs, glvnd) picks the vendor per
# GPU at run time, so multi-GPU machines use several at once.
ARG GPU_COMMON_PKGS="libvulkan1 vulkan-tools vainfo clinfo libgl1 libegl1 libgles2 firmware-misc-nonfree"
ARG GPU_AMD_PKGS="firmware-amd-graphics rocm-opencl-icd rocminfo rocm-smi libamdhip64-5"
ARG GPU_INTEL_PKGS="firmware-intel-graphics intel-media-va-driver-non-free libze1"
# The pattern matches every gpu-userspace deb the plan built for this
# architecture (profiles and levels come from the manifest, not from here).
# Nothing is active until dc-gpu-apply.service runs `dc-gpu apply` at boot, which
# activates the stored profile (`auto` when the installer recorded none).
RUN apt-get update \
    && set -- ${GPU_COMMON_PKGS} ${GPU_AMD_PKGS} ${GPU_INTEL_PKGS} 'gpu-userspace-*' \
    && apt-get install -y --no-install-recommends "$@"

# -----------------------------------------------------------------------------
# Phase 3.1: Kernel and its device modules
# -----------------------------------------------------------------------------
# The only layer that differs between the signed image and its `-nosign` twin: the
# project kernel (daemoncores-kernel-<kver>, built from kernel.org) is installed
# through the virtual name linux-image-${KERNEL_VARIANT}${KERNEL_SUFFIX}-${ARCH}.
# Debian's own linux-image-${ARCH} is not installed: a second /usr/lib/modules/<kver>/
# fails bootc lint. The standard image adds the same per-arch driver modules
# (linux-modules-*) so its hardware support does not shrink.
# Kernel variant: `minimal` (default) is the project kernel, the same as Containerfile.minimal.
ARG KERNEL_VARIANT=minimal
# arm64 only. The arm64 distribution ships two kernels because the page size is a
# compile-time choice (docs/Handoff-Decisions.md, "Two arm64 kernels"): the 4 KB kernel
# (KERNEL_SUFFIX empty) for Raspberry Pi 3 and 4, the 16 KB kernel (KERNEL_SUFFIX
# `-16k`) for recent hardware. KERNEL_SUFFIX completes the kernel package name
# (`-nosign` selects the unsigned-kernel twin) and ARM_DEVICES lists the device
# module packages that kernel serves. The CI passes the values per image; the
# defaults build the 4 KB one.
ARG ARM_DEVICES="rpi3 rpi4"
ARG KERNEL_SUFFIX=""
# Fingerprint of the kernel and device-module debs only, set by the CI. Declared here, not
# with DEBS_HASH, so a kernel rebuild re-runs this layer without re-running the heavy
# package layer above.
ARG KERNEL_DEBS_HASH=none
# The apt lists are wiped after every dpkg run (src/debianpreinstall/etc/apt/apt.conf.d/99-apt-clean),
# so this layer refreshes them itself, then installs the kernel and the device modules in one
# transaction.
RUN apt update \
    && set -- \
    && if [ "${ARCH}" != "amd64" ]; then \
        for _d in ${ARM_DEVICES}; do set -- "$@" "linux-modules-${_d}"; done; \
    fi \
    && apt install -y --no-install-recommends \
        linux-image-${KERNEL_VARIANT}${KERNEL_SUFFIX}-${ARCH} "$@"

# Host-side signature enforcement. The pipeline passes the repository's cosign
# public key and the image reference; both are empty until the key exists, in
# which case no policy is shipped (see src/basepostinstall).
ARG IMAGE_REF=""
ARG COSIGN_PUBKEY_B64=""
RUN /usr/libexec/debian-bootc/install-signature-policy "${IMAGE_REF}" "${COSIGN_PUBKEY_B64}"

# bootc images are updated in-place via ostree; no runtime healthcheck applies.
HEALTHCHECK NONE

# -----------------------------------------------------------------------------
# Phase 9: Version stamp — the aleph install metadata
# -----------------------------------------------------------------------------
# bootc install writes /sysroot/.bootc-aleph.json from the OCI metadata, and
# Debian's bootupd unit (bootupctl 0.3.x) parses it with a STRICT string schema:
# with these labels absent both fields are null and bootloader-update.service
# fails on EVERY boot (replayed and confirmed on 2026-10-30; see GPU-Support).
# The CI passes the build-arg (tag + sha); the label layers stay after every
# content layer so stamping never invalidates the build cache.
ARG IMAGE_VERSION=unversioned
ARG IMAGE_CREATED=2026-10-30T00:00:00Z
LABEL org.opencontainers.image.version="${IMAGE_VERSION}"
LABEL org.opencontainers.image.created="${IMAGE_CREATED}"
