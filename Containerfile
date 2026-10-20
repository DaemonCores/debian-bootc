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
# Asks the CI for two arm64 kernels (docs/decisions.md, "Two arm64 kernels"): the
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
RUN for _r in 1 2 3 4 5; do \
        rm -rf /var/lib/apt/lists/* && apt update && break; \
        [ "$_r" -lt 5 ] && sleep 30; \
    done \
    && apt install -y --no-install-recommends \
        git \
        curl \
        ${FIRMWARE_PKGS} \
        bootc \
        bootupd \
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
    fi

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
# compile-time choice (docs/decisions.md, "Two arm64 kernels"): the 4 KB kernel
# (KERNEL_SUFFIX empty) for Raspberry Pi 3 and 4, the 16 KB kernel (KERNEL_SUFFIX
# `-16k`) for recent hardware. KERNEL_SUFFIX completes the kernel package name
# (`-nosign` selects the unsigned-kernel twin) and ARM_DEVICES lists the device
# module packages that kernel serves. The CI passes the values per image; the
# defaults build the 4 KB one.
ARG ARM_DEVICES="rpi3 rpi4"
ARG KERNEL_SUFFIX=""
# The apt lists are wiped after every dpkg run (src/debianpreinstall/etc/apt/apt.conf.d/99-apt-clean),
# so this layer refreshes them itself, then installs the kernel and the device modules in one
# transaction.
RUN for _r in 1 2 3 4 5; do \
        apt update && break; \
        [ "$_r" -lt 5 ] && sleep 30; \
    done \
    && set -- \
    && if [ "${ARCH}" != "amd64" ]; then \
        for _d in ${ARM_DEVICES}; do set -- "$@" "linux-modules-${_d}"; done; \
    fi \
    && apt install -y --no-install-recommends \
        linux-image-${KERNEL_VARIANT}${KERNEL_SUFFIX}-${ARCH} "$@"

# -----------------------------------------------------------------------------
# Phase 4: ostree filesystem migration
# -----------------------------------------------------------------------------
# bootc/ostree requires /home, /root, /mnt, /srv, /opt as symlinks into /var so the
# read-only /usr tree can be swapped atomically while mutable state persists in /var.
# The layout script is shared with Containerfile.minimal (src/ostreelayout).
COPY ./src/debianpostinstall /
COPY ./src/ostreelayout /
RUN /usr/libexec/debian-bootc/ostree-layout \
    && systemctl enable ssh-host-keygen.service \
    && rm -f /etc/ssh/ssh_host_*

# Host-side signature enforcement. The pipeline passes the repository's cosign
# public key and the image reference; both are empty until the key exists, in
# which case no policy is shipped (see src/signaturepolicy).
ARG IMAGE_REF=""
ARG COSIGN_PUBKEY_B64=""
COPY ./src/signaturepolicy /
RUN /usr/libexec/debian-bootc/install-signature-policy "${IMAGE_REF}" "${COSIGN_PUBKEY_B64}"

# bootc images are updated in-place via ostree; no runtime healthcheck applies.
HEALTHCHECK NONE