# Night tasks (debian-bootc, P-988/P-989)
- [ ] T1: PR #152 (docs/L19-stable-cleanup -> develop) green and merged; red because of the strict gate (T5)
- [x] T2: tk align reports aligned for debian-bootc | proof: tk align | rg '"aligned": true'
- [x] T3: no dev content ahead on main: main has no commit that develop lacks, no force-push needed | proof: test -z "$(git log origin/develop..origin/main)"
- [x] T4: stable unpublished, edge published | proof: test "$(curl -s -o /dev/null -w '%{http_code}' https://daemoncores.github.io/debian-bootc/stable/gpg.key)" = 404
- [ ] T5: legacy code-law debt surfaced by the strict gate: mypy, pydoclint, 100% coverage, go stages gate-tests/gate-lint, jq test failures; RULES.md adaptation. Nothing weakened.
