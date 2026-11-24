# Blocked

## L4 installer walkthrough on a published ISO (P-936)
- Needs: a published ISO containing the installer fixes (DEBUG.md 19-24, 26). The published amd64 ISO 25bac424 predates them, a replay on it hits the already documented failures.
- Proof: `git log origin/main..HEAD --oneline` lists the unpushed fixes (debian-bootc and DaemonCores-CI); unpushed counts: 4 / 7 (debian-bootc / DaemonCores-CI), plus 1 wiki commit; the push waits for Full Pipeline run 45300399536 (a push to main cancels it).
- Unblock (owner): push both repos, let the pipeline publish the ISO, then run the UEFI walkthrough with every option and boot the installed disk.
- All other forge tickets (debian-bootc L1-L3, L5, L6; DaemonCores-CI L1-L6) are in review, awaiting that same run.
