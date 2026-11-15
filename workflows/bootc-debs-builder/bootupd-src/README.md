# bootupd source overlay — intentionally empty

Debian support is **upstream** since bootupd v0.4.0: `src/packagesystem.rs`
no longer hardcodes the rpm database, it delegates to a per-format script
(`packagesystem/query-file-owner-<fmt>`, dpkg included) that `install-all`
ships as the sysroot's `query-file-owner` when `PACKAGESYSTEM=dpkg`.

The local `packagesystem.rs.patch` that used to live here injected a dpkg
branch around the old `rpm_cmd` path. v0.4.0 rewrote `query_files` around the
script, so the patch stopped applying ("overlay drift", run 43655836093,
14/11) — it was deleted.

Keep this directory (and the `sources:` entry that references it): it is the
place for a future local delta, and dropping the directory would perturb the
package content hash for no reason.
