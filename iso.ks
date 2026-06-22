network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

reboot