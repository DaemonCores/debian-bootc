#####################################################################################
# Base image
# NOTE: use debian trixie not pined for auto security update
#####################################################################################
FROM debian:trixie
STOPSIGNAL SIGRTMIN+3

# Environment setup
LABEL org.opencontainers.image.title="Debian Trixie bootc"
LABEL org.opencontainers.image.description="Debian 13 Trixie bootable bootc/ostree container image, signed with cosign."
LABEL org.opencontainers.image.base.name="docker.io/library/debian:trixie"
LABEL org.opencontainers.image.source="https://github.com/DaemonCores/debian-bootc"
LABEL org.opencontainers.image.licenses="LGPL-2.1"
LABEL containers.bootc=1
LABEL ostree.bootable=1
# Asks the CI for two arm64 kernels (docs/decisions.md, "Two arm64 kernels"): the
# plain tag is built on the 16 KB kernel, and a second arm64-only image tagged
# `<tag>-4k` carries the 4 KB kernel for Raspberry Pi 3 and 4.
LABEL org.daemoncores.arm64-4k-image="true"

# Target architecture: amd64 (x86_64) default; CI overrides to arm64 via --build-arg ARCH=arm64.
# Drives the kernel package name linux-image-${KERNEL_VARIANT}-${ARCH} and the
# boot stack (${BOOT_PKG} is separate because arm64 does NOT follow grub-efi-${ARCH}).
ARG ARCH=amd64
# Boot profile, set by the CI from `LABEL org.daemoncores.boot-profile` (generic when
# absent): `generic` boots through UEFI with the Fedora GRUB (amd64, and arm64 PCs,
# servers, VMs); `embedded` is arm64 boards whose firmware loads U-Boot.
ARG BOOT_PROFILE=generic
# Kernel variant: `minimal` (default) is the project kernel built from kernel.org
# (daemoncores-kernel-<kver>), the same kernel as Containerfile.minimal.
ARG KERNEL_VARIANT=minimal
# arm64 only. The arm64 distribution ships two kernels because the page size is a
# compile-time choice (docs/decisions.md, "Two arm64 kernels"): the 4 KB kernel
# (KERNEL_SUFFIX empty) for Raspberry Pi 3 and 4, the 16 KB kernel (KERNEL_SUFFIX
# `-16k`) for recent hardware. KERNEL_SUFFIX completes the kernel package name and
# ARM_DEVICES lists the device module packages that kernel serves. The CI passes the
# values per image (16 KB on the plain arm64 tag, 4 KB on `<tag>-4k`); the defaults
# build the 4 KB one.
ARG KERNEL_SUFFIX=""
ARG ARM_DEVICES="rpi3 rpi4"
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
# SHA-256 checksum of the bootc APT repository signing key fetched below and
# the repository URL. The CI derives both at build time from the repository's
# APT_GPG_KEY secret; the defaults only serve local builds of the upstream
# repository and must be overridden for any other APT repository.
ARG BOOTC_APT_URL=https://daemoncores.github.io/debian-bootc
ARG BOOTC_GPG_SHA256=557c791d14da63c4621725fb335c6bd336c57afc6f1ffe3afcf25fc489b65680
# Product display name, injected by the CI from the repo name (dashes -> spaces).
# bootc-finalize brands the UEFI boot-entry label with it; empty falls back to
# /etc/os-release NAME.
ARG PRODUCT_NAME=""
# Setup all environement variables
ENV DEBIAN_FRONTEND=noninteractive
# Setup default shell with fail build on error
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# -----------------------------------------------------------------------------
# Phase 1: SSL prerequisites + APT sources (debianpreinstall)
# -----------------------------------------------------------------------------
COPY ./src/debianpreinstall /
RUN apt update \
    && apt install -y --no-install-recommends \
        ca-certificates \
        openssl \
        git \
        curl \
        wget \
    && sed -i "s|http://|https://|g" /etc/apt/sources.list.d/debian.sources \
    && rm -f \
        "/etc/ssl/certs/988a38cb.0" \
        "/etc/ssl/certs/NetLock_Arany_=Class_Gold=_Főtanúsítvány.pem" \
        "/usr/share/ca-certificates/mozilla/NetLock_Arany_=Class_Gold=_Főtanúsítvány.crt"

# -----------------------------------------------------------------------------
# Phase 2: Trust the bootc APT repository
# -----------------------------------------------------------------------------
COPY ./src/bootcpreinstall /
RUN sed -i -e "s/{{ ARCH }}/${ARCH}/g" -e "s|{{ APT_URL }}|${BOOTC_APT_URL%/}|g" \
        /etc/apt/sources.list.d/debian-bootc.sources \
    && wget \
        --progress=dot:giga \
        -O /usr/share/keyrings/debian-bootc-keyring.gpg \
        "${BOOTC_APT_URL%/}/gpg.key" \
    && printf '%s  /usr/share/keyrings/debian-bootc-keyring.gpg\n' "${BOOTC_GPG_SHA256}" \
        | sha256sum -c - \
    && mkdir -p /usr/lib/bootc \
    && printf '%s' "${PRODUCT_NAME}" > /usr/lib/bootc/product-name

# -----------------------------------------------------------------------------
# Phase 3: Install the ultra-minimal package set (arch-conditional via ARG)
# -----------------------------------------------------------------------------
# Both images run the single project kernel (daemoncores-kernel-<kver>, built from
# kernel.org), installed through the virtual name linux-image-${KERNEL_VARIANT}-${ARCH}.
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
RUN for _r in 1 2 3 4 5; do \
        rm -rf /var/lib/apt/lists/* && apt update && break; \
        [ "$_r" -lt 5 ] && sleep 30; \
    done \
    && apt install -y --no-install-recommends \
        linux-image-${KERNEL_VARIANT}${KERNEL_SUFFIX}-${ARCH} \
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
            firmware-nvidia-graphics \
            linux-modules-x86-64; \
    else \
        arm_modules=(); \
        for _d in ${ARM_DEVICES}; do arm_modules+=("linux-modules-${_d}"); done; \
        apt install -y --no-install-recommends \
            efibootmgr \
            libubootenv-tool \
            device-tree-compiler \
            linux-modules-arm${KERNEL_SUFFIX} \
            "${arm_modules[@]}"; \
    fi

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