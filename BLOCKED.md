# Blocked

## L4 installer walkthrough on a published ISO (P-936)
- Needs: a published ISO containing the installer fixes (DEBUG.md 19-24, 26). The published amd64 ISO 25bac424 predates them.
- State 2026-11-24: Full Pipeline run 45425967250 (dispatched on main, CI 2659ad9) has passed the APT key pin (entry 32 of DEBUG.md); `stable/gpg.key` answers 200. Container images are building; the ISO job follows. A push to debian-bootc main cancels this run, so the 1 local debian-bootc commit(s) (DEBUG.md only) wait for it; DaemonCores-CI has 0 unpushed commit(s).
- Proof: `git rev-list --count origin/main..HEAD` in each repo gives 1 / 0.
- Unblock: the run publishes the ISO, then the UEFI walkthrough with every option and a boot of the installed disk (needs a local VM on the published ISO).
- Other forge tickets stay in review awaiting that same run.
