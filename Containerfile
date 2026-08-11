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
# Drives kernel/headers package names: linux-image-${ARCH}, linux-headers-${ARCH}
# (Debian upstream kernel metapackages). The boot stack uses ${BOOT_PKG} (a
# separate ARG because arm64 does NOT follow the grub-efi-${ARCH} pattern).
ARG ARCH=amd64
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
# Arch-specific packages (kernel/headers) use the Debian upstream naming pattern
# linux-image-${ARCH}, linux-headers-${ARCH}, so there is no if/else on ARCH
# here. apt installs the upstream Debian kernel metapackage directly. The
# per-arch kernel modules are installed in a separate conditional RUN block
# below (after the main apt install) so each arch gets ALL its SBC-relevant
# modules in one go: amd64 -> linux-modules-x86_64; arm64 ->
# linux-modules-arm + rpi3/rpi4/rpi5/rk3588 overlays. The modules are OPTIONAL —
# the base image works without them. The boot stack uses ${BOOT_PKG} (separate
# ARG because arm64 does NOT follow grub-efi-${ARCH}). broadcom-sta-dkms is
# amd64-only and absent from Containerfile.minimal, so it is dropped here for
# parity. FIRMWARE_PKGS and APT_HOLD_PKG stay separate ARGs because they do NOT
# follow the name-${ARCH} pattern.
RUN apt update \
    && apt install -y \
        dkms \
        linux-image-${ARCH} \
        linux-headers-${ARCH} \
        ${FIRMWARE_PKGS} \
        bootc \
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
        dhcpcd \
        isc-dhcp-client \
        wpasupplicant \
        firstboot-user-setup \
        ${BOOT_PKG} \
    && apt-mark hold ${APT_HOLD_PKG} || true \
    && rm -rf \
        /tmp/* \
        /var/tmp/* \
        /run/* \
        /usr/sbin/policy-rc.d

# -----------------------------------------------------------------------------
# Phase 3.1: Per-arch kernel modules (optional)
# -----------------------------------------------------------------------------
# Install ALL modules matching the target arch. amd64 gets the x86_64 module
# set; arm64 gets the arm64 module set PLUS the Raspberry Pi 3/4/5 and Rockchip
# RK3588 SBC overlays so a single arm64 image boots on every SBC the project
# targets. The modules are OPTIONAL — the base kernel works without them, so a
# failure to find a module package (rare on non-SBC arm64 hosts) is tolerated.
# Replaces the previous per-device DEVICE build-arg + linux-modules-${DEVICE}
# pattern: the device dimension is now collapsed into the arch dimension.
RUN if [ "${ARCH}" = "amd64" ]; then \
        apt update \
        && apt install -y --no-install-recommends \
            linux-modules-x86_64 \
        && rm -rf /var/lib/apt/lists/*; \
    else \
        apt update \
        && apt install -y --no-install-recommends \
            linux-modules-arm \
            linux-modules-rpi3 \
            linux-modules-rpi4 \
            linux-modules-rpi5 \
            linux-modules-rk3588 \
        && rm -rf /var/lib/apt/lists/*; \
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
    && ln -s var/home / \
    && ln -s var/mnt / \
    && ln -s var/srv / \
    && ln -s var/opt / \
    && ln -s var/roothome /root \
    && ln -s sysroot/ostree /ostree \
    && ln -s var/usr/lib/locale /usr/lib/locale

# bootc images are updated in-place via ostree; no runtime healthcheck applies.
HEALTHCHECK NONE