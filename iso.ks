network --hostname={{ hostname }} --activate

zerombr
clearpart --all --initlabel
autopart --type=lvm --fstype=xfs

bootc --source-imgref=ghcr.io/{{ repo }}:latest \
      --target-imgref=ghcr.io/{{ repo }}:latest

%onerror
# Dumpez les logs bootc dans la console pour pouvoir diagnostiquer
echo "=== BOOTC ERROR ==="
journalctl -u anaconda --no-pager -n 100 || true
ls /tmp/anaconda*.log 2>/dev/null | xargs -I{} sh -c 'echo "=== {} ==="; cat {}'
%end

reboot