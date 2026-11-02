# dracut stage guard: dracut exits non-zero on explicitly --add'ed modules the
# tree does not ship (Fedora-only modules like anaconda / qemu-net on a Debian
# installer tree). Filter the stage options down to what the tree actually has.
# Kept as a separate file instead of a Containerfile heredoc: the CI runner's
# dockerfile parser does not support heredoc instructions.
import glob

p = glob.glob('/usr/lib/osbuild/stages/org.osbuild.dracut')[0]
src = open(p).read()
old = "    extra = options.get(\"extra\", [])"
new = """    extra = options.get("extra", [])

    # Cross-distro guard: drop --add/-m names whose module does not exist in
    # the tree (module dirs are <nn>-<name> under usr/lib/dracut/modules.d).
    _md = _os.path.join(tree, "usr/lib/dracut/modules.d")
    if add_modules or modules:
        _have = set()
        if _os.path.isdir(_md):
            for _n in _os.listdir(_md):
                _have.add(_n.split("-", 1)[-1].lower())
        add_modules = [m for m in add_modules if m.lower() in _have]
        modules = [m for m in modules if m.lower() in _have]"""
assert old in src, 'dracut stage shape changed'
src = src.replace(old, new, 1)
# main() takes (tree, options) but does not import os; add it at function scope
src = src.replace('def main(tree, options):\n    kernels = options["kernel"]',
                  'def main(tree, options):\n    import os as _os\n    kernels = options["kernel"]', 1)
open(p, 'w').write(src)
print('patched', p)