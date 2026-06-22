#####################################################################################
# Base image
# NOTE: use debian trixie not pined for auto security update
#####################################################################################
FROM debian:trixie

# SHA-256 checksum of the bootc APT repository signing key fetched below.
# Update this value whenever the key at
# https://daemoncores.github.io/debian-bootc/gpg.key is rotated.
ARG BOOTC_GPG_SHA256=557c791d14da63c4621725fb335c6bd336c57afc6f1ffe3afcf25fc489b65680

# Environment setup
LABEL org.opencontainers.image.title="Debian Trixie bootc"
LABEL org.opencontainers.image.description="Debian 13 Trixie bootable bootc/ostree container image, signed with cosign."
LABEL org.opencontainers.image.base.name="docker.io/library/debian:trixie"
LABEL org.opencontainers.image.source="https://github.com/DaemonCores/debian-bootc"
LABEL org.opencontainers.image.licenses="LGPL-2.5"
LABEL containers.bootc=1
LABEL ostree.bootable=1

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# Bootc filesystem migrations
RUN rm -rf /{home,root,mnt,srv,opt}  \
    && mkdir -p /var/{home,roothome,mnt,srv,opt} /sysroot \
    && ln -s /var/{home,mnt,srv,opt} / \
    && ln -s /var/roothome /root \
    && ln -sf sysroot/ostree /ostree

# Stage APT sources and bootc helper scripts before any apt update runs.
COPY ./src/debianpreinstall /

# Install SSL dependencies before use apt with https for fix ssl error
RUN apt update \
    && apt install -y \
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

COPY ./src/bootcpreinstall /  
RUN && wget \
        -O /usr/share/keyrings/debian-bootc-keyring.gpg \
        https://daemoncores.github.io/debian-bootc/gpg.key \
    && printf '%s  /usr/share/keyrings/debian-bootc-keyring.gpg\n' "${BOOTC_GPG_SHA256}" \
        | sha256sum -c - \
    && apt update \
    && apt install -y \
        dkms \
        linux-image-amd64 \
        linux-headers-amd64 \
        firmware-linux-free \
        firmware-linux \
        firmware-misc-nonfree \
        intel-microcode \
        amd64-microcode \
        bootc \

# Clean and purge image
RUN apt autoremove -y \
    && apt clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /var/log/apt/* \
        /var/log/dpkg.log \
        /var/log/alternatives.log \
        /tmp/* \
        /var/tmp/* \
        /run/* \
        /usr/sbin/policy-rc.d

# bootc images are updated in-place via ostree; no runtime healthcheck applies.
HEALTHCHECK NONE