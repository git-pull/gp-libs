"""Tests for doctree extraction and pure group projection."""

from __future__ import annotations

import doctest
import pathlib
import typing as t

import pytest
from docutils import nodes
from docutils.utils import new_document

from doctest_core import (
    BlockKind,
    ParseSettings,
    Phase,
    ProjectionSettings,
    Provider,
    build_registry,
    extract_blocks,
    parse_document,
    project,
)
from doctest_core.markup import _stamp_myst_source_lines


@pytest.fixture(params=["rst", "myst"])
def grouped_document(request: pytest.FixtureRequest) -> tuple[pathlib.Path, str]:
    """Return equivalent reStructuredText and MyST documents."""
    if request.param == "rst":
        return (
            pathlib.Path("guide.rst"),
            """
.. testsetup:: alpha, beta

   value = 40

.. doctest:: alpha, beta
   :options: +ELLIPSIS
   :skipif: False
   :pyversion: >=3.10

   >>> value + 2
   42

.. testcode:: alpha

   print(value + 3)

.. testoutput:: alpha
   :options: +NORMALIZE_WHITESPACE

   43

.. testcleanup:: alpha, beta

   del value
""",
        )
    return (
        pathlib.Path("guide.md"),
        """
```{testsetup} alpha, beta
value = 40
```

```{doctest} alpha, beta
:options: +ELLIPSIS
:skipif: False
:pyversion: ">=3.10"

>>> value + 2
42
```

```{testcode} alpha
print(value + 3)
```

```{testoutput} alpha
:options: +NORMALIZE_WHITESPACE

43
```

```{testcleanup} alpha, beta
del value
```
""",
    )


def test_extracts_sphinx_vocabulary_as_typed_data(
    grouped_document: tuple[pathlib.Path, str],
) -> None:
    """Both front ends preserve groups, gates, options, and source order."""
    path, source = grouped_document

    result = parse_document(
        source,
        path,
        settings=ParseSettings(),
        registry=build_registry(),
    )

    assert [block.kind for block in result.blocks] == [
        "testsetup",
        "doctest",
        "testcode",
        "testcleanup",
    ]
    assert [block.document_order for block in result.blocks] == [0, 1, 2, 4]
    assert [block.block_ordinal for block in result.blocks] == [0, 1, 2, 3]
    assert result.blocks[1].groups == ("alpha", "beta")
    assert result.blocks[1].options == {doctest.ELLIPSIS: True}
    assert result.blocks[1].skipif == "False"
    assert result.blocks[1].pyversion == ">=3.10"
    assert result.outputs[0].document_order == 3
    assert result.outputs[0].options == {doctest.NORMALIZE_WHITESPACE: True}
    assert not [item for item in result.diagnostics if item.level == "error"]


def test_projection_groups_without_merging_blocks(
    grouped_document: tuple[pathlib.Path, str],
) -> None:
    """One plan owns shared state while every source block keeps a recipe."""
    path, source = grouped_document
    parsed = parse_document(source, path, registry=build_registry())

    plans = project(
        parsed,
        document_name=path.name,
        settings=ProjectionSettings(),
        registry=build_registry(),
    )

    assert [plan.group for plan in plans] == ["alpha", "beta"]
    assert [block.phase for block in plans[0].blocks] == [
        Phase.SETUP,
        Phase.TEST,
        Phase.TEST,
        Phase.CLEANUP,
    ]
    assert [block.phase for block in plans[1].blocks] == [
        Phase.SETUP,
        Phase.TEST,
        Phase.CLEANUP,
    ]
    assert plans[0].blocks[1] is not plans[1].blocks[1]
    assert plans[0].blocks[1].name == "guide::alpha[1]"
    assert plans[1].blocks[1].name == "guide::beta[1]"
    assert plans[0].blocks[2].expected is not None
    assert plans[0].blocks[2].expected.text == "43\n"


def test_prompt_recipe_is_exactly_stdlib_normalized() -> None:
    """Projection preserves every field emitted by ``DocTestParser``."""
    source = """
>>> value = 1
>>> value + 1
2
>>> int('bad')
Traceback (most recent call last):
ValueError: invalid literal...
"""
    parsed = parse_document(source, pathlib.Path("guide.rst"))

    plan = project(parsed, document_name="guide")[0]
    recipes = plan.blocks[0].examples
    expected = (
        doctest.DocTestParser()
        .get_doctest(
            parsed.blocks[0].source,
            {},
            "guide",
            "guide.rst",
            0,
        )
        .examples
    )

    assert [tuple(recipe) for recipe in recipes] == [
        (
            example.source,
            example.want,
            example.exc_msg,
            example.lineno,
            example.indent,
            example.options,
        )
        for example in expected
    ]


def test_ungrouped_policy_is_explicit() -> None:
    """The projection setting chooses sharing without changing block identity."""
    parsed = parse_document(
        ">>> one = 1\n\nSome prose.\n\n>>> one + 1\n2\n",
        pathlib.Path("guide.rst"),
    )

    shared = project(
        parsed,
        document_name="guide",
        settings=ProjectionSettings(ungrouped="default"),
    )
    isolated = project(
        parsed,
        document_name="guide",
        settings=ProjectionSettings(ungrouped="block"),
    )

    assert [(plan.group, len(plan.blocks)) for plan in shared] == [("default", 2)]
    assert [(plan.group, len(plan.blocks)) for plan in isolated] == [
        ("block-0", 1),
        ("block-1", 1),
    ]


def test_anonymous_group_does_not_collide_with_named_group() -> None:
    """A generated block group cannot alias an author-declared group."""
    parsed = parse_document(
        """>>> anonymous = True

.. doctest:: block-0

   >>> named = True
""",
        pathlib.Path("guide.rst"),
    )

    plans = project(
        parsed,
        document_name="guide",
        settings=ProjectionSettings(ungrouped="block"),
    )

    assert len(plans) == 2
    assert len({plan.group for plan in plans}) == 2
    assert [[block.block_ordinal for block in plan.blocks] for plan in plans] == [
        [0],
        [1],
    ]


def test_parse_deduplicates_reporter_and_doctree_diagnostics() -> None:
    """One parser problem produces one typed diagnostic with its best line."""
    parsed = parse_document(
        ".. unknown-directive::\n",
        pathlib.Path("guide.rst"),
        settings=ParseSettings(suppressed_diagnostics=frozenset()),
    )

    errors = [
        diagnostic for diagnostic in parsed.diagnostics if diagnostic.level == "error"
    ]

    assert len(errors) == 1
    assert errors[0].code == "docutils.unknown-directive"
    assert errors[0].line == 1


def test_default_unknown_role_suppression_includes_lookup_companion() -> None:
    """Suppressing an unknown role removes both docutils messages."""
    parsed = parse_document(
        ":missing-role:`value`\n",
        pathlib.Path("guide.rst"),
    )

    assert not [
        diagnostic
        for diagnostic in parsed.diagnostics
        if "role" in diagnostic.message.lower()
    ]


def test_registered_block_kind_survives_generic_node_extraction() -> None:
    """Extraction preserves stamps while projection resolves their policy."""
    tree = new_document("guide.rst")
    node = nodes.literal_block(
        ">>> 6 * 7\n42\n",
        ">>> 6 * 7\n42\n",
        testnodetype="example",
        groups=["shared"],
    )
    node.source = "guide.rst"
    node.line = 1
    tree += node

    class Contributor:
        provider = Provider("example", "1")

        def contribute(self, registrar: t.Any) -> None:
            """Register the node stamp's projection policy."""
            registrar.add_block_kind(
                "example",
                BlockKind(Phase.TEST, "prompt", None),
            )

    registry = build_registry([Contributor()])
    parsed = extract_blocks(tree, registry=registry)
    plans = project(parsed, document_name="guide.rst", registry=registry)

    assert parsed.blocks[0].kind == "example"
    assert plans[0].blocks[0].examples[0].source == "6 * 7\n"


def test_unregistered_stamp_does_not_rename_runnable_blocks() -> None:
    """Foreign node metadata cannot consume a runnable identity ordinal."""
    tree = new_document("guide.rst")
    tree += nodes.literal_block(
        "foreign",
        "foreign",
        testnodetype="foreign",
    )
    tree += nodes.doctest_block(">>> 6 * 7\n42\n", ">>> 6 * 7\n42\n")

    parsed = extract_blocks(tree)

    assert [(block.kind, block.block_ordinal) for block in parsed.blocks] == [
        ("doctest", 0),
    ]


def test_extraction_rejects_malformed_typed_text_stamps() -> None:
    """Dynamic node metadata cannot violate the public parsed-record types."""
    tree = new_document("guide.rst")
    node = nodes.literal_block(
        ">>> 6 * 7\n42\n",
        ">>> 6 * 7\n42\n",
        testnodetype="doctest",
        groups=["shared"],
        skipif=123,
    )
    tree += node

    with pytest.raises(TypeError, match="skipif node attribute"):
        extract_blocks(tree)


def test_registered_block_kind_pairs_with_custom_output_stamp() -> None:
    """A block kind can name an output stamp without parser changes."""
    tree = new_document("guide.rst")
    code = nodes.literal_block(
        'print("answer")',
        'print("answer")',
        testnodetype="example",
        groups=["shared"],
    )
    code.source = "guide.rst"
    code.line = 1
    output = nodes.literal_block(
        "answer",
        "answer",
        testnodetype="expected",
        groups=["shared"],
    )
    output.source = "guide.rst"
    output.line = 3
    tree += code
    tree += output

    class Contributor:
        provider = Provider("example", "1")

        def contribute(self, registrar: t.Any) -> None:
            """Register the custom executable and output relationship."""
            registrar.add_block_kind(
                "example",
                BlockKind(Phase.TEST, "exec", "expected"),
            )

    registry = build_registry([Contributor()])
    parsed = extract_blocks(tree, registry=registry)
    plans = project(parsed, document_name="guide.rst", registry=registry)

    assert parsed.outputs[0].kind == "expected"
    assert plans[0].blocks[0].expected is not None
    assert plans[0].blocks[0].expected.text == "answer\n"


@pytest.mark.parametrize("body", ["", "value = 42"])
def test_prompt_free_doctest_does_not_project_a_group(body: str) -> None:
    """A doctest directive without examples cannot become a host item."""
    parsed = parse_document(
        f".. doctest::\n\n   {body}\n",
        pathlib.Path("guide.rst"),
    )

    assert project(parsed, document_name="guide.rst") == ()


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            pathlib.Path("guide.rst"),
            """
.. testcode::
   :trim-doctest-flags:

   print("answer")

.. testoutput::
   :no-trim-doctest-flags:

   answer
""",
        ),
        (
            pathlib.Path("guide.md"),
            """
```{testcode}
:trim-doctest-flags:
print("answer")
```

```{testoutput}
:no-trim-doctest-flags:
answer
```
""",
        ),
    ],
)
def test_testcode_output_accept_sphinx_trim_options(
    path: pathlib.Path,
    source: str,
) -> None:
    """Standalone parsers accept Sphinx's full trim-option vocabulary."""
    parsed = parse_document(source, path)

    assert [block.kind for block in parsed.blocks] == ["testcode"]
    assert [output.kind for output in parsed.outputs] == ["testoutput"]
    assert not [item for item in parsed.diagnostics if item.level == "error"]


def test_myst_directive_line_is_document_absolute() -> None:
    """MyST-local content offsets do not replace the fence's document line."""
    parsed = parse_document(
        """Heading
=======
```{doctest}
>>> 1 + 1
3
```
""",
        pathlib.Path("guide.md"),
    )

    assert parsed.blocks[0].line == 4
    plan = project(parsed, document_name="guide.md")[0]
    assert plan.blocks[0].lineno == 3

    with_options = parse_document(
        """Heading
=======
```{doctest}
:options: +ELLIPSIS

>>> 1 + 1
3
```
""",
        pathlib.Path("guide.md"),
    )

    assert with_options.blocks[0].line == 6


@pytest.mark.parametrize(
    ("source", "expected_line"),
    [
        ("Text\n\n    >>> 1 + 1\n    2\n", 3),
        ("Text\n\n```\n>>> 1 + 1\n2\n```\n", 4),
    ],
)
def test_myst_bare_prompt_line_distinguishes_indent_and_fence(
    source: str,
    expected_line: int,
) -> None:
    """Standalone MyST stamps the first executable source line."""
    parsed = parse_document(source, pathlib.Path("guide.md"))

    assert parsed.blocks[0].line == expected_line


def test_myst_line_stamper_does_not_attribute_included_source_to_root() -> None:
    """Root text cannot supply an absolute line for an included node."""
    tree = new_document("guide.md")
    node = nodes.literal_block(
        ">>> 1 + 1\n2\n",
        ">>> 1 + 1\n2\n",
        testnodetype="doctest",
    )
    node.source = "included.md"
    node.line = 1
    tree += node

    _stamp_myst_source_lines(tree, "Text\n\n>>> 1 + 1\n2\n")
    parsed = extract_blocks(tree)

    assert parsed.blocks[0].path == pathlib.Path("included.md")
    assert parsed.blocks[0].line == 2


def test_output_pairing_is_group_local_and_latest_wins() -> None:
    """Other groups do not break pairing and later output replaces earlier."""
    source = """
.. testcode:: alpha

   print("alpha")

.. testcode:: beta

   print("beta")

.. testoutput:: alpha

   stale

.. testoutput:: alpha

   alpha

.. testoutput:: beta

   beta
"""
    parsed = parse_document(source, pathlib.Path("guide.rst"))

    plans = project(parsed, document_name="guide")

    assert [plan.group for plan in plans] == ["alpha", "beta"]
    assert plans[0].blocks[0].expected is not None
    assert plans[0].blocks[0].expected.text == "alpha\n"
    assert plans[1].blocks[0].expected is not None
    assert plans[1].blocks[0].expected.text == "beta\n"
