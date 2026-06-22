# personal-server net-install kickstart
# Anaconda pulls the bootc image from GHCR at install time.

network --hostname=alma-builder

# Pull the bootc image from the registry
bootc --source-imgref=ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

# Reboot after install
reboot
