network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

%post
AUSER=$(getent passwd 1000 | cut -d: -f1)
if [ -n "$AUSER" ]; then
    AHASH=$(getent shadow "$AUSER" | cut -d: -f2)
    AGECOS=$(getent passwd "$AUSER" | cut -d: -f5)
    AUID=$(getent passwd "$AUSER" | cut -d: -f3)
    AGID=$(getent passwd "$AUSER" | cut -d: -f4)
    IN_WHEEL=$(id -nG "$AUSER" | grep -qw wheel && echo yes || echo no)

    userdel "$AUSER" 2>/dev/null || true
    rm -rf "/home/${AUSER}"

    groupadd --gid "$AGID" "$AUSER" 2>/dev/null || true
    useradd                              \
        --home-dir    "/home/${AUSER}"   \
        --uid         "$AUID"            \
        --gid         "$AGID"            \
        --shell       /bin/bash          \
        --comment     "$AGECOS"          \
        --create-home "$AUSER"

    usermod -p "$AHASH" "$AUSER"

    for grp in adm systemd-journal cdrom audio video plugdev netdev; do
        getent group "$grp" && usermod -aG "$grp" "$AUSER" || true
    done

    if [ "$IN_WHEEL" = "yes" ]; then
        usermod -aG sudo,wheel "$AUSER"
    fi
fi
%end