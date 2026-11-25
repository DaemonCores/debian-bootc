"""Remove precompiled selinux file_contexts binaries from the osbuild stage.

See Containerfile.bib for the why. Kept as a separate file instead of a
Containerfile heredoc: the CI runner's dockerfile parser does not support
heredoc instructions.
"""

import glob

PATCH_GLOB = "/usr/lib*/python3*/site-packages/osbuild/util/selinux.py"

path = glob.glob(PATCH_GLOB)[0]
with open(path, encoding="utf-8") as handle:
    src = handle.read()
old = '    for path in paths:\n        subprocess.run(["setfiles", "-F",'
new = """    for _bin in (*__import__('glob').glob(spec_file + '.bin'),
                 *__import__('glob').glob(spec_file + '.homedirs.bin')):
        try:
            os.remove(_bin)
        except OSError:
            pass

    for path in paths:
        subprocess.run(["setfiles", "-F","""
assert old in src, "selinux.py shape changed"
with open(path, "w", encoding="utf-8") as handle:
    _ = handle.write(src.replace(old, new, 1))
print("patched", path)
