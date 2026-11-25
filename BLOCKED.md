# BLOCKED (2026-11-25 18:11)
Remaining after the stable cleanup (T2-T4 done, see NIGHT-TASKS.md). Both are one body of work: the strict tk gate of the code-law template fails on this repository's legacy code.

## T1
kind: command
claim: PR #152 cannot merge: the strict gate (coverage 100%, mypy, pydoclint, go stages) is red on the legacy code, so the PR stays unmerged until T5 is fixed.
cmd: gh pr view 152 --json mergeStateStatus,statusCheckRollup --jq '[.statusCheckRollup[]|select(.conclusion=="FAILURE")]|length|if .>0 then error("red") else "green" end'

## T5
kind: command
claim: the gate still fails: test coverage 86.63% below 100%, mypy 9 errors, pydoclint missing, no gate stage for go code, 2 jq tests fail on the runner (run 45653658220). Fixing is multi-day code-law adoption, not started tonight; nothing was weakened.
cmd: gh run view 45653658220 --json conclusion --jq 'if .conclusion=="success" then "ok" else error("failure") end'
