#####################################################################################
# Base image
#####################################################################################
FROM debian:trixie

# Environement Setup
LABEL org.opencontainers.image.title="Debian Trixie"
LABEL org.opencontainers.image.description="Debian 13 Trixie bootc"
LABEL org.opencontainers.image.base.name="docker.io/library/debian:trixie"
LABEL containers.bootc=1
LABEL ostree.bootable=1

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# Bootc filesystem migrations
RUN rm -rf /{home,root,mnt,srv,opt}  \
    && mkdir -p /var/{home,roothome,mnt,srv,opt} /sysroot \
    && ln -s /var/{home,mnt,srv,opt} / \
    && ln -s  /var/roothome /root \
    && ln -sf sysroot/ostree /ostree

# Prepare package
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
        "/etc/ssl/certs/NetLock_Arany_=Class_Gold=_Főtanúsítvány.pem"

COPY ./src/bootcpreinstall /  
RUN wget \
        -O /usr/share/keyrings/debian-bootc-keyring.gpg \
        https://daemoncores.github.io/debian-bootc/gpg.key \
    && apt update \
    && apt install -y \
        dracut \
        iproute2 \
        linux-image-amd64 \
        linux-headers-amd64 \
        firmware-linux-free \
        firmware-linux \
        firmware-misc-nonfree \
        intel-microcode \
        amd64-microcode \
        dkms \
        grub-efi-amd64 \
        grub-efi-amd64-signed \
        shim-signed \
        lvm2 \
        xfsprogs \
        bootc

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

RUN KVER=$(ls -1v /usr/lib/modules | tail -1) \
    && cp /boot/vmlinuz-${KVER} /usr/lib/modules/${KVER}/vmlinuz \
    && rm -rf /boot/* \
    && dracut \
        --kver "${KVER}" \
        --force /usr/lib/modules/${KVER}/initramfs.img
