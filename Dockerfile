#####################################################################################
# Base image
#####################################################################################
FROM debian:trixie AS base

# Environement Setup
LABEL org.opencontainers.image.title="Debian Trixie"
LABEL org.opencontainers.image.description="Debian 13 Trixie bootc"
LABEL org.opencontainers.image.base.name="docker.io/library/debian:trixie"

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-c"]

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
    && sed -i "s|http://|https://|g" /etc/apt/sources.list.d/debian.sources \
    && apt update

#####################################################################################
# Bootc build image
#####################################################################################
FROM base AS bootc-builder
ENV CARGO_HOME=/build/rust \
    RUSTUP_HOME=/build/rust \
    OSTREE_VER=2026.1 \
    BOOTC_VER=v1.16.1

# Prepare package
COPY ./src/bootcpreinstall /
RUN apt install -y \
        make \
        build-essential \
        go-md2man \
        libzstd-dev \
        pkgconf \
        autoconf \
        automake \
        libtool \
        libglib2.0-dev \
        libcurl4-openssl-dev \
        libgpgme-dev \
        libarchive-dev \
        libmount-dev \
        libfuse3-dev \
        libssl-dev \
        libsystemd-dev \
        gobject-introspection \
        libgirepository1.0-dev \
        libsoup-3.0-dev \
        bison

# Ostree build and install
RUN mkdir -p /{build,debs} \
    && curl -fsSL \
        https://github.com/ostreedev/ostree/releases/download/v${OSTREE_VER}/libostree-${OSTREE_VER}.tar.xz \
        | tar -xJ -C /build \
    && cd /build/libostree-${OSTREE_VER} \
    && ./configure --prefix=/usr --sysconfdir=/etc \
        --disable-gtk-doc --disable-man \
    && make -j$(nproc) \
    && make -j$(nproc) install DESTDIR=/output/ostree \
    && dpkg-shlibdeps -O $(find . -name "libostree-1.so*" ! -name "*.la" | head -1) \
        2>/dev/null | sed 's/shlibs:Depends=//' > /tmp/ostree-deps \
    && DEPS=$(cat /tmp/ostree-deps) \
    && sed -i \
        -e "s|{{ VER }}|${OSTREE_VER}|g" \
        -e "s|{{ DEPS }}|${DEPS}|g" \
        /output/ostree/DEBIAN/control \
    && dpkg-deb --build /output/ostree /debs/libostree_${OSTREE_VER}_amd64.deb \
    && apt install -y /debs/libostree_${OSTREE_VER}_amd64.deb

# Bootc build and install
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- --profile minimal -y \
    && git clone --depth=1 --branch "${BOOTC_VER}" \
        https://github.com/bootc-dev/bootc.git /build/bootc \
    && curl -fsSL \
        https://github.com/bootc-dev/bootc/releases/download/${BOOTC_VER}/bootc-${BOOTC_VER#v}-vendor.tar.zstd \
        | tar --zstd -x -C /build/bootc \
    && . ${RUSTUP_HOME}/env \
    && cargo build --release --manifest-path /build/bootc/Cargo.toml \
    && make -j$(nproc) -C /build/bootc manpages DESTDIR=/output/bootc \
    && make -C /build/bootc install-all DESTDIR=/output/bootc \
    && dpkg-shlibdeps -O /build/bootc/target/release/bootc \
        2>/dev/null | sed 's/shlibs:Depends=//' > /tmp/bootc-deps \
    && DEPS=$(cat /tmp/bootc-deps) \
    && sed -i \
        -e "s|{{ VER }}|${BOOTC_VER#v}|g" \
        -e "s|{{ DEPS }}|${DEPS}|g"  \
        /output/bootc/DEBIAN/control \
    && dpkg-deb --build /output/bootc /debs/bootc_${BOOTC_VER#v}_amd64.deb \
    && rm -rf /{build,output}

#####################################################################################
# Final image
#####################################################################################
FROM base AS final

COPY --from=bootc-builder /debs/*.deb /tmp/
RUN apt install -y /tmp/*.deb && rm /tmp/*.deb

# Clean and purge image
RUN apt autoremove -y \
    && apt clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/sbin/policy-rc.d

COPY ./src/bootcpostinstall /
RUN KVER=$(ls -1v /usr/lib/modules | tail -1) \
    && rm -f \
        /boot/initrd.img* \
        /boot/initrd*.img \
    && dracut \
        --kver "${KVER}" \
        --force /usr/lib/modules/${KVER}/initramfs.img