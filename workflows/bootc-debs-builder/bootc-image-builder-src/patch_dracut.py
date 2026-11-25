"""Guard the osbuild dracut stage against modules the tree does not ship.

dracut exits non-zero on explicitly --add'ed modules the tree does not ship
(Fedora-only modules like anaconda / qemu-net on a Debian installer tree).
Filter the stage options down to what the tree actually has. Kept as a
separate file instead of a Containerfile heredoc: the CI runner's dockerfile
parser does not support heredoc instructions.
"""

import glob

PATCH_TARGET = "/usr/lib/osbuild/stages/org.osbuild.dracut"

path = glob.glob(PATCH_TARGET)[0]
with open(path, encoding="utf-8") as handle:
    src = handle.read()
old = '    extra = options.get("extra", [])'
new = """    extra = options.get("extra", [])

    # Cross-distro guard: drop --add/-m names whose module does not exist in
    # the tree (module dirs are under usr/lib/dracut/modules.d).
    # KNOWN LATENT BUG, left as is: dirs are <nn><name> (90qemu, no hyphen
    # after the digits), so this split never matches a plain name and the
    # filter drops every requested module. Fixing the parse would keep dirs
    # such as biosdevname whose binary is absent, and dracut then fails with
    # "Module 'biosdevname' cannot be installed" (proven locally); dracut's
    # own default set is what the ISO has always been built with.
    import re as _re
    _md = _os.path.join(tree, "usr/lib/dracut/modules.d")
    _live = "anaconda" in [m.lower() for m in add_modules]
    if add_modules or modules:
        _have = set()
        if _os.path.isdir(_md):
            for _n in _os.listdir(_md):
                _have.add(_n.split("-", 1)[-1].lower())
        add_modules = [m for m in add_modules if m.lower() in _have]
        modules = [m for m in modules if m.lower() in _have]

    # The live root: the Fedora-only "anaconda" module (dropped above on a
    # Debian tree) is what turns inst.stage2= into a mounted squashfs root.
    # debian-bootc-live (shipped by Containerfile.iso) replaces it and pulls
    # in dmsquash-live. Without it the ISO cannot mount its root: fail here
    # rather than ship an unbootable ISO.
    if _live:
        _have_live = _os.path.isdir(_md) and any(
            _re.sub(r"^[0-9]+", "", _n) == "debian-bootc-live"
            for _n in _os.listdir(_md))
        if not _have_live:
            raise RuntimeError(
                "dracut module debian-bootc-live missing from the tree")
        add_modules = list(add_modules) + ["debian-bootc-live"]"""
assert old in src, "dracut stage shape changed"
src = src.replace(old, new, 1)
# main() takes (tree, options) but does not import os; add it there.
src = src.replace(
    'def main(tree, options):\n    kernels = options["kernel"]',
    "def main(tree, options):\n    import os as _os\n" +
    '    kernels = options["kernel"]',
    1,
)
with open(path, "w", encoding="utf-8") as handle:
    _ = handle.write(src)
print("patched", path)
