# Gotcha: a new kernel series can lack the BORE patch

## What happened

Checked on 2026-10-19: kernel.org lists 7.3 as `mainline` and 7.2.11 as `stable`
(https://www.kernel.org/releases.json). The CachyOS patch repository has a `7.3/` directory,
but its `sched/` folder only holds `0001-bore-cachy.patch`; the `0001-bore.patch` that
`kernel/patches.yml` downloads exists in `7.2/` (https://github.com/CachyOS/kernel-patches/tree/master/7.2/sched)
and not in `7.3/` (HTTP 404). Without that patch the kernel has no `CONFIG_SCHED_BORE`, which
`kernel/config` sets, so `check_kconfig.py` fails with "not declared by this kernel".

## Rule

Do not pin the kernel by hand to get past it. The `track:` block of `linux-image` in
`packages.yml` uses `require-patches: kernel/patches.yml`, so the build picks the newest release
whose series provides every patch (7.2.x here) and moves up once the series has the file.
If the CachyOS file is renamed for good, change the URL in `kernel/patches.yml` instead.

## Verified

`check_kconfig.py --tree` (symbol declaration check only) passed for the arm64 4 KB, arm64 16 KB
and amd64 fragment sets on 7.2.11 with `0001-bore.patch` applied. The second pass (`--config`,
which needs `make olddefconfig`) was not run: no working compiler or container runtime on the
machine used. It is left to the first CI build.
