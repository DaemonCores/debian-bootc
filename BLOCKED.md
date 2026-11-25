# BLOCKED (2026-11-25 18:58)
T2-T5 are done (see NIGHT-TASKS.md). One item left, and it needs an owner decision on the global git hook.

## T1
kind: command
claim: PR #153 cannot merge green. Its "lint / check" job runs check_docs.py against the wiki master, which still cites the pre-rename overlay path workflows/bootc-debs-builder/bootc-installer-src (4 citations). The fix is committed on the wiki branch docs/tk-6ccc13 (e588019, fast-forward of master) but pushing the wiki master is refused by the global git hook (git_hook.py ci_green asks GitHub for check-runs of the wiki repo, which answers 404 because a wiki has none: "CI proof for master unreadable ... denied"). I do not bypass the hook. Decision for the owner: let the hook accept a wiki master push (the wiki has no CI), or publish e588019 to the wiki master.
cmd: gh pr view 153 --json statusCheckRollup --jq '[.statusCheckRollup[]|select(.conclusion=="FAILURE")]|length|if .>0 then error("red") else "ok" end'
