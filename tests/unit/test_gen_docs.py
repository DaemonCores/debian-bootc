"""Unit tests for scripts/gen_docs.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gen_docs


def test_shell_header_extracts_comment_block(tmp_path: Path) -> None:
    """The header is the comment block right after the shebang.

    Args:
        tmp_path: Scratch directory holding the sample script.
    """
    script = tmp_path / "s.sh"
    script.write_text(
        "#!/bin/bash\n#\n# name - purpose\n# more\nset -e\n# x\n",
        encoding="utf-8"
    )
    assert gen_docs._shell_header(script) == "name - purpose\nmore"


def test_page_replaces_only_generated_region() -> None:
    """Text outside the markers survives regeneration."""
    current = f"intro\n{gen_docs.START}\nold\n{gen_docs.END}\noutro\n"
    new = gen_docs._page("T", "new", current)
    assert new.startswith("intro\n")
    assert new.endswith("\noutro\n")
    assert "old" not in new
    assert "new" in new
