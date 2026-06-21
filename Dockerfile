#####################################################################################
# Base image
#####################################################################################
FROM debian:trixie

# Environement Setup
LABEL org.opencontainers.image.title="Debian Trixie"
LABEL org.opencontainers.image.description="Debian 13 Trixie bootc"
LABEL org.opencontainers.image.base.name="docker.io/library/debian:trixie"

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# Bootc filesystem migrations
RUN rm -rf /{home,root,mnt,srv,opt}  \
    && mkdir -p /var/{home,roothome,mnt,srv,opt} \
    && ln -s /var/{home,mnt,srv,opt} / \
    && ln -s  /var/roothome /root

# Prepare package
COPY ./src/debianpreinstall /
RUN apt update \
    && apt install -y \
        ca-certificates \
        openssl \
        git \
        curl \
        wget \
    && sed -i "s|http://|https://|g" /etc/apt/sources.list.d/debian.sources

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
        bootc || (echo "=== dpkg.log ===" \
            && grep -i "bootc\|error\|fail" /var/log/dpkg.log \
            && echo "=== apt/term.log ===" \
            && cat /var/log/apt/term.log \
            && false)

# Clean and purge image
RUN apt autoremove -y \
    && apt clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/sbin/policy-rc.d

RUN KVER=$(ls -1v /usr/lib/modules | tail -1) \
    && rm -f \
        /boot/initrd.img* \
        /boot/initrd*.img \
    && dracut \
        --kver "${KVER}" \
        --force /usr/lib/modules/${KVER}/initramfs.img