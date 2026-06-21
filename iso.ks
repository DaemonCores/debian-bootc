# personal-server net-install kickstart
# Anaconda pulls the bootc image from GHCR at install time.

network --hostname=alma-builder

# Pull the bootc image from the registry
ostreecontainer --url=ghcr.io/daemoncores/almabuilder:latest --no-signature-verification

# Reboot after install
reboot
