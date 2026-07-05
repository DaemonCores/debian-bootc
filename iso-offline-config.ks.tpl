network --bootproto=dhcp --hostname={{ hostname }} --activate
# Prevent Anaconda's timezone module from enabling chronyd (it ignores
# services --disabled=chronyd). --nontp is the only effective knob.
timezone --nontp

bootc --source-imgref=oci-archive:/run/install/repo/image.tar --target-imgref=ghcr.io/{{ repo }}:latest

%post
# Default root password for debug if first boot setup don't run
echo 'root:BootcDebug@0' | chpasswd
chage -d 0 root

# User creation and SSH root login are handled by firstboot-user-setup.service on first boot.
# Remove any SSH config Anaconda may have set.
rm -f /etc/ssh/sshd_config.d/01-permitrootlogin.conf

# Queue Secure Boot MOK enrollment for the first reboot
# The administrator will be prompted at the blue MokManager screen.
# Password: root password set above (changed by firstboot-user-setup on first login).
CERT=/usr/share/debian-bootc/sb_signing.crt
if [ -f "$CERT" ] && command -v mokutil >/dev/null 2>&1; then
    if ! mokutil --test-key "$CERT" 2>/dev/null; then
        echo 'BootcDebug@0' | mokutil --import "$CERT" --root-pw
        echo "Secure Boot: MOK enrollment queued. Confirm at next reboot (MokManager)."
    fi
fi
%end