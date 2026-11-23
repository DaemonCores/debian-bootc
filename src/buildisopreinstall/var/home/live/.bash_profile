# Start the graphical installer automatically on tty1.
if [ "$(tty)" = "/dev/tty1" ]; then
    # Without a GPU render node (VM without virtio-gpu, plain framebuffer) cage
    # and GTK4 must fall back to software rendering: both refuse to start
    # (cage) or draw garbage (GTK's GL renderer on llvmpipe) otherwise.
    if ! ls /dev/dri/renderD* >/dev/null 2>&1; then
        export WLR_RENDERER_ALLOW_SOFTWARE=1 WLR_RENDERER=pixman GSK_RENDERER=cairo
    fi
    exec cage -- bootc-installer
fi
