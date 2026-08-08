"""Acceptance tests for consuming Sphinx-resolved doctrees."""

from __future__ import annotations

import pathlib
import typing as t

from docutils import nodes
from docutils.utils import new_document

from doctest_core import extract_blocks

if t.TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp

    from .conftest import MakeAppParams


def test_extracts_hidden_blocks_from_sphinx_resolved_doctree(
    make_app: t.Callable[..., SphinxTestApp],
    make_app_params: MakeAppParams,
    tmp_path: pathlib.Path,
) -> None:
    """Resolved includes retain Sphinx comment nodes and source ownership."""
    included_path = tmp_path / "examples.rst"
    included_path.write_text(
        """.. testsetup:: shared

   value = 40

.. doctest:: shared

   >>> value + 2
   42

.. testcleanup:: shared

   del value
""",
        encoding="utf8",
    )
    args, kwargs = make_app_params(
        index="""Resolved page
=============

.. include:: examples.rst
""",
        confoverrides={"extensions": ["sphinx.ext.doctest"]},
    )
    app = make_app(*args, **kwargs)
    app.build()
    doctree = app.env.get_and_resolve_doctree("index", app.builder)

    sphinx_hidden_kinds = [
        str(node["testnodetype"])
        for node in doctree.findall(nodes.comment)
        if node.get("testnodetype") in {"testsetup", "testcleanup"}
    ]
    assert sphinx_hidden_kinds == ["testsetup", "testcleanup"]

    result = extract_blocks(doctree)

    assert [block.kind for block in result.blocks] == [
        "testsetup",
        "doctest",
        "testcleanup",
    ]
    assert {block.path for block in result.blocks} == {included_path}
    assert [block.hidden for block in result.blocks] == [True, False, True]
    assert all(block.line is not None for block in result.blocks)


def test_sphinx_docstring_source_has_unknown_file_line() -> None:
    """Docstring-relative node lines are not fabricated as file locations."""
    tree = new_document("module.rst")
    node = nodes.literal_block(
        ">>> 6 * 7\n42\n",
        ">>> 6 * 7\n42\n",
        testnodetype="doctest",
        groups=["shared"],
    )
    node.source = "/tmp/:docstring of package.module"
    node.line = 7
    tree += node

    result = extract_blocks(tree)

    assert result.blocks[0].line is None
