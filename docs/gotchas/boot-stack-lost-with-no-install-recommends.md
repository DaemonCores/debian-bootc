# Gotcha: the login and console stack disappears with `--no-install-recommends`

## What happened

After the standard image stopped installing recommends, the amd64 boot reached the
login stage with `systemd-logind`, `ssh` and `console-setup` reported as FAILED on the
serial console. The last image that booted
(`linux-image-6.12.95+deb13-amd64`) carried `systemd-sysv`, `libpam-systemd`,
`dbus-user-session`, `kbd` and `keyboard-configuration`; none of them is in the explicit
install list of the `Containerfile`, they only came in as recommends.

## Status

This is a hypothesis, not a confirmed root cause: no image could be built or booted
where it was found (no container runtime on the workstation, and the cancelled CI runs
never reached the boot test). The five packages are installed explicitly again
[src: file: Containerfile:187-191]; the next boot test of the CI decides whether the
hypothesis holds.

## What NOT to do

- Do not remove DRM or any driver to make a boot test pass.
- Do not hide the FAILED units with `FailureAction` overrides: the logind drop-in
  `headless.conf` only keeps a failed logind from stopping the machine.
- Do not drop a recommend from the install list without checking it against the package
  list of the last booting image.
