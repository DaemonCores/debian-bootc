network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=registry:ghcr.io/{{ repo }}:latest --target-imgref=ghcr.io/{{ repo }}:latest

%post
# Récupérer l'user créé par anaconda (UID >= 1000)
AUSER=$(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1; exit}')

if [ -n "$AUSER" ]; then
    # Sauvegarder le hash du mot de passe et la présence dans wheel
    AHASH=$(getent shadow "$AUSER" | cut -d: -f2)
    IN_WHEEL=$(id -nG "$AUSER" | grep -qw wheel && echo yes || echo no)

    # Supprimer l'user anaconda (useradd → dash, pas de skel propre)
    userdel -r "$AUSER" 2>/dev/null || true

    # Recréer proprement avec adduser (bash, skel, home correct)
    adduser --disabled-password --gecos "" "$AUSER"

    # Restaurer le mot de passe
    usermod -p "$AHASH" "$AUSER"

    # Groupes Debian standard
    for grp in adm systemd-journal cdrom audio video plugdev netdev; do
        getent group "$grp" && usermod -aG "$grp" "$AUSER" || true
    done

    # sudo uniquement si anaconda avait mis l'user dans wheel
    if [ "$IN_WHEEL" = "yes" ]; then
        usermod -aG sudo,wheel "$AUSER"
    fi
fi
%end