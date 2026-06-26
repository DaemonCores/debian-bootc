network --bootproto=dhcp --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

%post
# Default root password for debug if first boot setup don't run
echo 'root:BootcDebug@0' | chpasswd
chage -d 0 root

# User creation and SSH root login are handled by firstboot-user-setup.service on first boot.
# Remove any SSH config Anaconda may have set.
rm -f /etc/ssh/sshd_config.d/01-permitrootlogin.conf
%end