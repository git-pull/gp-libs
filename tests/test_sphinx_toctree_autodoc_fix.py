import pathlib
import textwrap
import typing as t

import pytest

from docutils import nodes
from sphinx import addnodes
from sphinx.testing.util import SphinxTestApp, assert_node

if t.TYPE_CHECKING:
    from .conftest import MakeAppParams


class ToCTreeTestFixture(t.NamedTuple):
    test_id: str
    text: str


FIXTURES = [
    ToCTreeTestFixture(
        test_id="basic",
        text=textwrap.dedent(
            """
.. autoclass:: doctest_docutils.DocutilsDocTestFinder
   :members:
   :show-inheritance:
   :undoc-members:

contents:

.. contents::
   :local:

toctree:

.. toctree::
   :local:
"""
        ),
    ),
]


@pytest.mark.parametrize(
    ToCTreeTestFixture._fields, FIXTURES, ids=[f.test_id for f in FIXTURES]
)
def test_toc_shows_api_docs(
    make_app: t.Callable[[t.Any], SphinxTestApp],
    make_app_params: "MakeAppParams",
    test_id: str,
    text: str,
) -> None:
    """Assert sphinx_toctree_autodoc_fix collects entries from autodoc.

    Normal sphinx ToC does not collect them< see sphinx-doc#6316
    """
    args, kwargs = make_app_params(
        index=text,
        confoverrides={
            "extensions": ["sphinx_toctree_autodoc_fix", "sphinx.ext.autodoc"],
            "html_theme": "basic",
        },
    )
    app = make_app(*args, **kwargs)
    app.build()

    content = (pathlib.Path(app.outdir) / "index.html").read_text(encoding="utf8")

    assert "DocutilsDocTestFinder" in content
    assert "Table of Contents" in content
    assert 'href="#doctest_docutils.DocutilsDocTestFinder' in content

    toctree = app.env.tocs["index"]
    assert "DocutilsDocTestFinder" == toctree[0][0].astext()
    assert_node(
        toctree[1][0],
        [nodes.list_item, addnodes.compact_paragraph],
    )
