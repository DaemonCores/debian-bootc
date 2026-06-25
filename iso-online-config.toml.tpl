# ISO online-install config template
# Variables: {{ hostname }}, {{ display_name }}, {{ volume_id }}, {{ repo }}

[customizations.installer.kickstart]
contents = """
network --bootproto=dhcp --activate --onboot=on

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

%post
# User creation and SSH root login are handled by firstboot-user-setup.service on first boot.
# Remove any SSH config Anaconda may have set.
rm -f /etc/ssh/sshd_config.d/01-permitrootlogin.conf
%end
"""

# Disable Anaconda Users module:
# User account setup is handled by firstboot-user-setup.service.
# This removes both the user creation screen and the SSH root checkbox from the UI.
[customizations.installer.modules]
disable = ["org.fedoraproject.Anaconda.Modules.Users"]

[customizations.iso]
volume_id      = "{{ volume_id }}_NET"
application_id = "{{ display_name }} Installer"
publisher      = "{{ display_name }}"