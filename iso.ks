network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

%pre
sysctl -w user.max_user_namespaces=1000000
%end

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

reboot