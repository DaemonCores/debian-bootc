#!/bin/sh
# systemd generator. dmsquash-live's generator creates sysroot.mount only if
# root=live:... is known when generators run, which is before any dracut
# cmdline hook (and /etc is read-only then, so nothing can be written for it).
# Without sysroot.mount, initrd-switch-root is never queued: the boot stops
# after dracut-pre-pivot. Derive the live root from inst.stage2 here and hand
# it to the dmsquash-live generator through its $root variable.
command -v getarg > /dev/null || . /lib/dracut-lib.sh
. /lib/debian-bootc-live/inst-stage2-lib.sh
_root=$(debian_bootc_live_root)
[ -z "$_root" ] || root=$_root
export root
exec "${0%/*}/dracut-dmsquash-generator" "$@"
