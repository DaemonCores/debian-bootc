network --bootproto=dhcp --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=oci-archive:/run/install/repo/image.tar --target-imgref=ghcr.io/{{ repo }}:latest

%post
# User creation and SSH root login are handled by firstboot-user-setup.service on first boot.
# Remove any SSH config Anaconda may have set.
rm -f /etc/ssh/sshd_config.d/01-permitrootlogin.conf
%end