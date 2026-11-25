# BLOCKED (2026-11-25 19:00)
T2-T5 are done (see NIGHT-TASKS.md). T1 is the only task left.

## T1
kind: command
claim: PR #153 stays red on "lint / check" because the wiki master (77eafb5) does not hold the citation fix e588019. Pushing the wiki master is refused by the global git hook: git push origin master in debian-bootc.wiki answers "REFUSED by global git hook: CI proof for master unreadable (github GET /repos/DaemonCores/debian-bootc.wiki/commits/e588019.../check-runs -> HTTP 404)". A wiki has no check-runs and tk has no local_by state for it, so the hook cannot be satisfied; I do not bypass it. The owner must allow a wiki master push or publish e588019.
cmd: git ls-remote https://github.com/DaemonCores/debian-bootc.wiki.git master | grep -q e588019
