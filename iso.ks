network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
part /boot/efi --fstype=vfat --size=600
part /boot --fstype=ext4 --size=1024
part pv.01 --grow
volgroup vg_{{ hostname }} pv.01
logvol / --vgname=vg_{{ hostname }} --name=root --grow --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

reboot