# Night tasks (debian-bootc, P-988/P-989)
- [x] T1: PR #153 merged into develop, wiki master holds e588019 | proof: gh pr view 153 --json state --jq 'if .state=="MERGED" then "ok" else error("not merged") end'
- [x] T2: tk align reports aligned for debian-bootc | proof: tk align | rg '"aligned": true'
- [x] T3: no dev content ahead on main: main has no commit that develop lacks, no force-push needed | proof: test -z "$(git log origin/develop..origin/main)"
- [x] T4: stable unpublished, edge published | proof: test "$(curl -s -o /dev/null -w '%{http_code}' https://daemoncores.github.io/debian-bootc/stable/gpg.key)" = 404
- [x] T5: legacy code-law debt surfaced by the strict gate: lint, types, docs, 100% coverage, siblings and CI checkout provisioned; nothing weakened | proof: gh run view 45679609476 --json jobs --jq '[.jobs[]|select(.name|test("^(lint|test|audit|e2e|rules)"))|.conclusion]|all(.=="success")|if . then "ok" else error("red") end'
