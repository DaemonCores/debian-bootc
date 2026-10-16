# Start the graphical installer automatically on tty1.
if [ "$(tty)" = "/dev/tty1" ]; then
    exec cage -- bootc-installer
fi
