network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

%post
for grp in adm systemd-journal cdrom audio video plugdev; do
    getent group $grp && usermod -aG $grp $(getent passwd 1000 | cut -d: -f1) || true
done
%end