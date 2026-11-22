#!/bin/bash
# Live-root bridge for the bootc-image-builder installer ISO on Debian.
#
# bootc-image-builder boots the ISO with Anaconda arguments
# (inst.stage2=hd:LABEL=<volume label>) and relies on the Fedora-only
# "anaconda" dracut module to turn them into a mounted live root. Debian's
# dracut has no such module, so this module does the translation and pulls
# in dmsquash-live, which does the actual squashfs mount.

check() {
    return 0
}

depends() {
    echo dmsquash-live
    return 0
}

installkernel() {
    # The squashfs is mounted through a loop device from the ISO9660 volume,
    # with an overlay on top: none of these are autoloaded in the initramfs.
    instmods squashfs overlay loop isofs
}

install() {
    inst_simple "$moddir/inst-stage2-lib.sh" /lib/debian-bootc-live/inst-stage2-lib.sh
    inst_hook cmdline 29 "$moddir/parse-inst-stage2.sh"
    inst_script "$moddir/live-generator.sh" \
        "$systemdutildir"/system-generators/debian-bootc-live-generator
}
