#!/bin/sh
# Shared by the cmdline hook and the systemd generator.
# The rootfs squashfs sits at images/install.img on the ISO (bootc-image-builder
# layout, not the LiveOS/squashfs.img dracut defaults to).

# Prints the dracut live root (live:<device>) derived from inst.stage2=hd:<device>[:<path>],
# nothing when root= is already given or inst.stage2 is not an hd: one.
debian_bootc_live_root() {
    [ -z "$(getarg root=)" ] || return 0

    _stage2=$(getarg inst.stage2=)
    case "$_stage2" in
        hd:*) ;;
        *) return 0 ;;
    esac

    _dev=${_stage2#hd:}
    _dev=${_dev%%:*}
    [ -n "$_dev" ] || return 0
    echo "live:${_dev}"
}

# Writes the live-root arguments to /etc/cmdline.d (getarg re-reads that
# directory on each call). Cmdline stage only: /etc is read-only when the
# systemd generators run.
debian_bootc_live_args() {
    _root=$(debian_bootc_live_root)
    [ -n "$_root" ] || return 0

    # squashfs/overlay/loop/isofs are loaded explicitly: mount(8) does not
    # autoload them inside the initramfs, the live root is then "not found".
    {
        echo "root=${_root}"
        echo "rd.live.dir=images rd.live.squashimg=install.img rd.live.image"
        echo "rd.driver.pre=squashfs,overlay,loop,isofs"
    } >> /etc/cmdline.d/90-debian-bootc-live.conf
}
