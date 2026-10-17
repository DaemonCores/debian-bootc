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

# Target architecture: amd64 (x86_64) default; CI overrides to arm64 via --build-arg ARCH=arm64.
# Drives the kernel package name via linux-image-${KERNEL_VARIANT}-${ARCH} and the
# boot stack (${BOOT_PKG} is separate because arm64 does NOT follow grub-efi-${ARCH}).
ARG ARCH=amd64
# Kernel variant: `stock` (default) installs linux-image-stock-${ARCH}, which is provided
# by the custom linux-image-common deb published by bootc-debs-builder via Provides:.
# The Debian archive has no linux-image-stock-<arch> package, so this name only resolves
# once the custom deb is published. Using the virtual name avoids installing Debian's
# kernel (linux-image-amd64/arm64) which would create a second /usr/lib/modules/<deb-kver>/
# directory and fail bootc lint. See packages.yml linux-image BUILD section.
ARG KERNEL_VARIANT=stock
# Boot stack: grub-efi-amd64-signed (x86_64) or u-boot-tools (arm64 SBCs). Kept as a
# separate ARG because arm64 does NOT follow the grub-efi-${ARCH} pattern).
ARG BOOT_PKG=grub-efi-amd64-signed
# Firmware packages: x86_64 includes microcode + full firmware; arm64 drops microcode.
ARG FIRMWARE_PKGS="intel-microcode amd64-microcode firmware-linux-free firmware-linux firmware-misc-nonfree"
# Package(s) to hold from auto-upgrade: grub-efi-amd64-signed (x86_64); empty on arm64.
ARG APT_HOLD_PKG=grub-efi-amd64-signed
# Per-arch kernel modules. The image installs ALL modules matching the
# target arch in a separate conditional RUN block below (after the main apt
# install): x86_64 -> linux-modules-x86_64; arm64 -> linux-modules-arm plus the
# SBC overlays (rpi3/rpi4/rpi5/rk3588). The modules are OPTIONAL — the base image
# works without them.
# SHA-256 checksum of the bootc APT repository signing key fetched below.
# Update this value whenever the key at
# https://daemoncores.github.io/debian-bootc/gpg.key is rotated.
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
RUN sed -i "s/{{ ARCH }}/${ARCH}/g" \
        /etc/apt/sources.list.d/debian-bootc.sources \
    && wget \
        -O /usr/share/keyrings/debian-bootc-keyring.gpg \
        https://daemoncores.github.io/debian-bootc/gpg.key \
    && printf '%s  /usr/share/keyrings/debian-bootc-keyring.gpg\n' "${BOOTC_GPG_SHA256}" \
        | sha256sum -c - \
    && mkdir -p /usr/lib/bootc \
    && printf '%s' "${PRODUCT_NAME}" > /usr/lib/bootc/product-name

# -----------------------------------------------------------------------------
# Phase 3: Install the ultra-minimal package set (arch-conditional via ARG)
# -----------------------------------------------------------------------------
# Kernel package resolves via the virtual name linux-image-${KERNEL_VARIANT}-${ARCH}
# (default: linux-image-stock-amd64 / linux-image-stock-arm64) which is Provided by
# the custom linux-image-common deb from bootc-debs-builder. This prevents Debian's
# kernel (linux-image-amd64/arm64) from being co-installed, which would create a
# second /usr/lib/modules/<deb-kver>/ directory and fail bootc lint.
# linux-headers is NOT installed: it was never published to the custom apt repo
# and Debian's linux-headers-${ARCH} would create a spurious /usr/lib/modules/<kver>/build.
# Per-arch kernel modules are installed in a separate conditional RUN block
# below (Phase 3.1): amd64 -> linux-modules-x86-64; arm64 -> linux-modules-arm +
# rpi3/rpi4/rpi5/rk3588 overlays.
RUN apt update \
    && apt install -y \
        linux-image-${KERNEL_VARIANT}-${ARCH} \
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
    && { [ -z "${APT_HOLD_PKG}" ] || apt-mark hold "${APT_HOLD_PKG}"; } \
    && apt update \
    && if [ "${ARCH}" = "amd64" ]; then \
        apt install -y --no-install-recommends \
            linux-modules-x86-64; \
    else \
        apt install -y --no-install-recommends \
            linux-modules-arm \
            linux-modules-rpi3 \
            linux-modules-rpi4 \
            linux-modules-rpi5 \
            linux-modules-rk3588; \
    fi

# -----------------------------------------------------------------------------
# Phase 4: ostree filesystem migration
# -----------------------------------------------------------------------------
# bootc/ostree requires /home, /root, /mnt, /srv, /opt as symlinks into /var so the
# read-only /usr tree can be swapped atomically while mutable state persists in /var.
# Mirrors the main Containerfile exactly; do NOT change the layout or bootc fails.
COPY ./src/debianpostinstall /
RUN mkdir -p /var/home \
        /var/roothome \
        /var/mnt \
        /var/srv \
        /var/opt \
        /var/usr/lib/locale \
        /sysroot/ostree \
    && cp -r /usr/lib/locale/* /var/usr/lib/locale/ || true \
    && rm -rf /home \
        /root \
        /mnt \
        /srv \
        /opt \
        /usr/lib/locale \
        /tmp/* \
        /var/tmp/* \
        /run/* \
        /usr/sbin/policy-rc.d \
    && ln -s var/home / \
    && ln -s var/mnt / \
    && ln -s var/srv / \
    && ln -s var/opt / \
    && ln -s var/roothome /root \
    && ln -s sysroot/ostree /ostree \
    && ln -s var/usr/lib/locale /usr/lib/locale

# bootc images are updated in-place via ostree; no runtime healthcheck applies.
HEALTHCHECK NONE