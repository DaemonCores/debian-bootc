# Blocked

## L4 installer walkthrough on a published ISO (P-936)
- Needs: a published ISO containing the installer fixes (DEBUG.md 19-24, 26). The published amd64 ISO 25bac424 predates them.
- State 2026-11-24: every publish is broken until DaemonCores-CI fix/L21-drop-channel (drop_channels input; `vars` is not available in composite actions, DEBUG.md 33) is on CI main. That commit is staged but refused by the global git hook (`git_hook.py:68`: docs pointer must be staged, while `docs` is gitignored in DaemonCores-CI since 40e29b7). Owner decision: fix the hook for an ignored docs, or allow `git add -f docs`.
- Proof: `git rev-list --count origin/main..HEAD` in each repo gives 1 / 0.
- Unblock: the run publishes the ISO, then the UEFI walkthrough with every option and a boot of the installed disk (needs a local VM on the published ISO).
- Other forge tickets stay in review awaiting that same run.
