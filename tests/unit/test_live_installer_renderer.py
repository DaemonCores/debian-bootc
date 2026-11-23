"""Live ISO installer session must force the pixman renderer without a GPU."""

import re
from pathlib import Path

PROFILE = (
    Path(__file__).resolve().parents[2] / 'src' / 'buildisopreinstall' / 'var' /
    'home' / 'live' / '.bash_profile'
)


def test_no_render_node_forces_pixman_renderer() -> None:
    """Without pixman, GLES2 on llvmpipe leaves cage black on bochs-drm."""
    text = PROFILE.read_text()
    block = re.search(r'if ! ls /dev/dri/renderD\*.*?\bfi\b', text, re.S)
    assert block is not None
    assert 'WLR_RENDERER=pixman' in block.group(0)
