# Drop the precompiled selinux file_contexts .bin files from the osbuild
# selinux stage (see Containerfile.bib for the why). Kept as a separate file
# instead of a Containerfile heredoc: the CI runner's dockerfile parser does
# not support heredoc instructions.
import glob

p = glob.glob('/usr/lib*/python3*/site-packages/osbuild/util/selinux.py')[0]
src = open(p).read()
old = "    for path in paths:\n        subprocess.run([\"setfiles\", \"-F\","
new = """    for _bin in (*__import__('glob').glob(spec_file + '.bin'),
                 *__import__('glob').glob(spec_file + '.homedirs.bin')):
        try:
            os.remove(_bin)
        except OSError:
            pass

    for path in paths:
        subprocess.run(["setfiles", "-F","""
assert old in src, 'selinux.py shape changed'
open(p, 'w').write(src.replace(old, new, 1))
print('patched', p)