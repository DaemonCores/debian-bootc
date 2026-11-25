# BLOCKED (2026-11-25 19:02)
T2-T5 are done (see NIGHT-TASKS.md). T1 is the only task left.

## T1
kind: command
claim: the wiki master must receive commit e588019 (citation fix) before PR #153 can be green, and git push origin master in debian-bootc.wiki is refused. Exact output of that push: "REFUSED by global git hook: CI proof for master unreadable (github GET /repos/DaemonCores/debian-bootc.wiki/commits/e588019214b5dd0cbd8429cd35f9e62f6c4b57c6/check-runs?per_page=100 -> HTTP 404: Not Found): denied." The refusing code is ~/.claude/hooks/flow/git_hook.py ci_green()/pre_push(): every protected branch needs green check-runs and a wiki repository has none. tk init never marked this wiki local_by, so the local-gate alternative (tk.local_gate_green) does not apply either. The hook is the owner's judge and I do not bypass it. The proof command fails while the wiki master (77eafb5) lacks the fix.
cmd: git ls-remote https://github.com/DaemonCores/debian-bootc.wiki.git master | grep -q e588019
