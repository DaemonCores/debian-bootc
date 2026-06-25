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
LABEL org.opencontainers.image.licenses="LGPL-2.5"
LABEL containers.bootc=1
LABEL ostree.bootable=1

# SHA-256 checksum of the bootc APT repository signing key fetched below.
# Update this value whenever the key at
# https://daemoncores.github.io/debian-bootc/gpg.key is rotated.
ARG BOOTC_GPG_SHA256=557c791d14da63c4621725fb335c6bd336c57afc6f1ffe3afcf25fc489b65680
# Setup all environement variables
ENV DEBIAN_FRONTEND=noninteractive
# Setup default shell with fail build on error
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# Fix ostree filesystem
RUN mkdir -p /sysroot/ostree /var/lib/locale && \
    for d in home mnt srv opt; do \
        [ -d "/${d}" ] && mv "/${d}" "/var/${d}" || true; \
    done && \
    [ -d /root ] && mv /root /var/roothome || true && \
    for d in home mnt srv opt; do \
        ln -sf "var/${d}" "/${d}"; \
    done && \
    ln -sf var/roothome /root && \
    ln -sf sysroot/ostree /ostree && \
    cp -a /usr/lib/locale/. /var/lib/locale/ 2>/dev/null || true && \
    rm -rf /usr/lib/locale && \
    ln -s /var/lib/locale /usr/lib/locale

# Bootc filesystem migrations
# All symlink require relative path because anaconda setup mount root disk in /mnt insted of /
# Install SSL dependencies before use apt with https for fix ssl error
COPY ./src/debianpreinstall /
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

# Install bootc and kernel for baseimage
# Clean and purge image
COPY ./src/bootcpreinstall /  
RUN wget \
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
        isc-dhcp-client \
        wpasupplicant \
        broadcom-sta-dkms \
        firstboot-user-setup \
    && rm -rf \
        /tmp/* \
        /var/tmp/* \
        /run/* \
        /usr/sbin/policy-rc.d

COPY ./assets/banner/etc /etc/etc/

# bootc images are updated in-place via ostree; no runtime healthcheck applies.
HEALTHCHECK NONE