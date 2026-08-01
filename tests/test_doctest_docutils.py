"""Tests for doctest_docutils."""

from __future__ import annotations

import doctest
import logging
import textwrap
import typing as t

import pytest

import doctest_docutils

if t.TYPE_CHECKING:
    import pathlib

FixtureFileDict = dict[str, str]


class DocTestFinderFixture(t.NamedTuple):
    """Test fixture for doctest_docutils."""

    # pytest
    test_id: str

    # Content
    files: FixtureFileDict
    tests_found: int


FIXTURES = [
    #
    # Docutils
    #
    DocTestFinderFixture(
        test_id="reST-doctest_block",
        files={
            "example.rst": textwrap.dedent(
                """
>>> 4 + 4
8
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="reST-doctest_directive",
        files={
            "example.rst": textwrap.dedent(
                """
.. doctest::

   >>> 4 + 4
   8
        """,
            ),
        },
        tests_found=1,
    ),
    #
    # Markdown / myst-parser
    #
    DocTestFinderFixture(
        test_id="MyST-doctest_block",
        files={
            "example.md": textwrap.dedent(
                """
```
>>> 4 + 4
8
```
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="MyST-doctest_block-python",
        files={
            "example.md": textwrap.dedent(
                """
```python
>>> 4 + 4
8
```
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="MyST-doctest_block-indented",
        files={
            "example.md": textwrap.dedent(
                """
Here's a test:

    >>> 4 + 4
    8
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="MyST-doctest_directive-colons",
        files={
            "example.md": textwrap.dedent(
                """
:::{doctest}

    >>> 4 + 4
    8
:::
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="MyST-doctest_directive-backticks",
        files={
            "example.md": textwrap.dedent(
                """
```{doctest}

    >>> 4 + 4
    8
```
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="MyST-doctest_directive-eval-rst-colons",
        files={
            "example.md": textwrap.dedent(
                """
:::{eval-rst}

   .. doctest::

      >>> 4 + 4
      8
:::
        """,
            ),
        },
        tests_found=1,
    ),
    DocTestFinderFixture(
        test_id="MyST-doctest_directive-eval-rst-backticks",
        files={
            "example.md": textwrap.dedent(
                """
```{eval-rst}

   .. doctest::

      >>> 4 + 4
      8
```
        """,
            ),
        },
        tests_found=1,
    ),
    # sphinx-inline-tabs
    DocTestFinderFixture(
        test_id="MyST-doctest_block-python--sphinx-inline-tabs",
        files={
            "example.md": textwrap.dedent(
                """
````{tab} example tab
```python
>>> 4 + 4
8
```
````

````{tab} example second
```python
>>> 4 + 2
6
```
````
        """,
            ),
        },
        tests_found=2,
    ),
]


class FilePathModeNotImplemented(Exception):
    """Raised if file_path_mode not supported."""

    def __init__(self, file_path_mode: str) -> None:
        super().__init__(f"No file_path_mode supported for {file_path_mode}")


@pytest.mark.parametrize(
    DocTestFinderFixture._fields,
    FIXTURES,
    ids=[f.test_id for f in FIXTURES],
)
@pytest.mark.parametrize("file_path_mode", ["relative", "absolute"])
def test_DocutilsDocTestFinder(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    test_id: str,
    files: FixtureFileDict,
    tests_found: int,
    file_path_mode: str,
) -> None:
    """Test for doctest_docutils."""
    # Initialize variables
    tests_path = tmp_path / "tests"
    first_test_key = next(iter(files.keys()))
    first_test_filename = first_test_key
    if file_path_mode == "absolute":
        first_test_filename = str(tests_path / first_test_filename)
    elif file_path_mode != "relative":
        raise FilePathModeNotImplemented(file_path_mode)

    tests_path.mkdir()
    for file_name, text in files.items():
        rst_file = tests_path / file_name
        rst_file.write_text(
            text,
            encoding="utf-8",
        )

    if file_path_mode == "relative":
        monkeypatch.chdir(tests_path)

    # Test
    finder = doctest_docutils.DocutilsDocTestFinder()
    text, _ = doctest._load_testfile(  # type: ignore
        str(first_test_filename),
        package=None,
        module_relative=False,
        encoding="utf-8",
    )
    tests = finder.find(text, str(first_test_filename))
    tests.sort(key=lambda test: test.name)

    assert len(tests) == tests_found

    for test in tests:
        doctest.DebugRunner(verbose=False).run(test)


class DocumentOrderFixture(t.NamedTuple):
    """Page of eleven numbered blocks, enough for name order to diverge.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    file_name : str
        Page name, whose suffix picks the parser.
    page : str
        Page content: block ``n`` evaluates to ``n``.
    """

    test_id: str
    file_name: str
    page: str


DOCUMENT_ORDER_FIXTURES = [
    DocumentOrderFixture(
        test_id="MyST-fences",
        file_name="example.md",
        page="\n".join(f"```python\n>>> {n}\n{n}\n```\n" for n in range(11)),
    ),
    DocumentOrderFixture(
        test_id="reST-doctest_blocks",
        file_name="example.rst",
        page="\n".join(f">>> {n}\n{n}\n" for n in range(11)),
    ),
]


@pytest.mark.parametrize(
    DocumentOrderFixture._fields,
    DOCUMENT_ORDER_FIXTURES,
    ids=[f.test_id for f in DOCUMENT_ORDER_FIXTURES],
)
def test_finder_collects_in_document_order(
    tmp_path: pathlib.Path,
    test_id: str,
    file_name: str,
    page: str,
) -> None:
    """Blocks come back in the order a reader meets them, not in name order.

    Sorting by name put ``page.md[10]`` ahead of ``page.md[1]``.
    """
    page_path = tmp_path / file_name
    page_path.write_text(page, encoding="utf-8")

    tests = doctest_docutils.DocutilsDocTestFinder().find(page, str(page_path))

    assert [test.examples[0].source.strip() for test in tests] == [
        str(n) for n in range(11)
    ]


class DoctestOptReTestCase(t.NamedTuple):
    """Test fixture for doctestopt_re regex.

    Backported from Sphinx commit ad0c343d3 (2025-01-04).
    https://github.com/sphinx-doc/sphinx/commit/ad0c343d3

    The original Sphinx test verified HTML output doesn't have trailing
    whitespace after flag trimming. This test verifies the regex correctly
    matches and removes leading whitespace before doctest flags.

    Refs: sphinx-doc/sphinx#13164
    """

    test_id: str
    input_code: str
    expected_output: str


DOCTESTOPT_RE_FIXTURES = [
    DoctestOptReTestCase(
        test_id="trailing-spaces-before-flag",
        input_code="result = func()   # doctest: +SKIP",
        expected_output="result = func()",
    ),
    DoctestOptReTestCase(
        test_id="tab-before-flag",
        input_code="result = func()\t# doctest: +SKIP",
        expected_output="result = func()",
    ),
    DoctestOptReTestCase(
        test_id="no-space-before-flag",
        input_code="result = func()# doctest: +SKIP",
        expected_output="result = func()",
    ),
    DoctestOptReTestCase(
        test_id="multiline-with-leading-whitespace",
        input_code="line1\nresult = func()   # doctest: +SKIP\nline3",
        expected_output="line1\nresult = func()\nline3",
    ),
    DoctestOptReTestCase(
        test_id="multiple-flags-on-separate-lines",
        input_code="a = 1  # doctest: +SKIP\nb = 2  # doctest: +ELLIPSIS",
        expected_output="a = 1\nb = 2",
    ),
    DoctestOptReTestCase(
        test_id="mixed-tabs-and-spaces",
        input_code="result = func() \t # doctest: +NORMALIZE_WHITESPACE",
        expected_output="result = func()",
    ),
]


@pytest.mark.parametrize(
    DoctestOptReTestCase._fields,
    DOCTESTOPT_RE_FIXTURES,
    ids=[f.test_id for f in DOCTESTOPT_RE_FIXTURES],
)
def test_doctestopt_re_whitespace_trimming(
    test_id: str,
    input_code: str,
    expected_output: str,
) -> None:
    """Verify doctestopt_re removes leading whitespace before doctest flags.

    Regression test for Sphinx PR #13164.
    Backported from Sphinx commit ad0c343d3 (2025-01-04).
    """
    result = doctest_docutils.doctestopt_re.sub("", input_code)
    assert result == expected_output


def test_doctest_finder_name_does_not_exist_message() -> None:
    """DocTestFinderNameDoesNotExist reports the offending object's type."""
    exc = doctest_docutils.DocTestFinderNameDoesNotExist("not-a-module")

    assert "DocTestFinder.find: name must be given" in str(exc)
    assert repr(str) in str(exc)


def test_docutils_package_relative_error_message() -> None:
    """TestDocutilsPackageRelativeError states the module-relative constraint."""
    exc = doctest_docutils.TestDocutilsPackageRelativeError()

    assert str(exc) == "Package may only be specified for module-relative paths."


def test_inline_flags_survive_a_directive(tmp_path: pathlib.Path) -> None:
    """A ``# doctest:`` flag applies even where the rendered code drops it.

    ``.. doctest::`` trims the flag out of the code a reader sees and keeps the
    original on the node, so the finder has to read the original.
    """
    page = textwrap.dedent(
        """
.. doctest::

    >>> print("a  b")  # doctest: +NORMALIZE_WHITESPACE
    a b
        """,
    )
    page_path = tmp_path / "page.rst"
    page_path.write_text(page, encoding="utf-8")

    (test,) = doctest_docutils.DocutilsDocTestFinder().find(page, str(page_path))
    runner = doctest.DocTestRunner(verbose=False)
    runner.run(test, out=lambda _: None)

    assert test.examples[0].options[doctest.NORMALIZE_WHITESPACE] is True
    assert runner.failures == 0


class DirectiveOptionFixture(t.NamedTuple):
    """Directive whose options reach the examples it holds.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    page : str
        reStructuredText page holding one ``.. doctest::`` directive.
    flag : int
        Option flag to read off the collected example.
    enabled : bool
        Whether the flag is expected on.
    """

    test_id: str
    page: str
    flag: int
    enabled: bool


DIRECTIVE_OPTION_FIXTURES = [
    DirectiveOptionFixture(
        test_id="directive-options-reach-the-example",
        page=".. doctest::\n    :options: +ELLIPSIS\n\n    >>> 2 + 2\n    4\n",
        flag=doctest.ELLIPSIS,
        enabled=True,
    ),
    DirectiveOptionFixture(
        test_id="an-inline-flag-beats-the-directive",
        page=".. doctest::\n    :options: +ELLIPSIS\n\n"
        "    >>> 2 + 2  # doctest: -ELLIPSIS\n    4\n",
        flag=doctest.ELLIPSIS,
        enabled=False,
    ),
]


@pytest.mark.parametrize(
    DirectiveOptionFixture._fields,
    DIRECTIVE_OPTION_FIXTURES,
    ids=[f.test_id for f in DIRECTIVE_OPTION_FIXTURES],
)
def test_directive_options_apply_per_example(
    test_id: str,
    page: str,
    flag: int,
    enabled: bool,
) -> None:
    """``:options:`` sets a block's defaults; an example's own flags win."""
    (test,) = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert test.examples[0].options[flag] is enabled


OUT_OF_ORDER_LINES_REST = [
    (
        "nested-in-a-directive",
        textwrap.dedent(
            """
Title
=====

>>> outer = 1

.. note::

   >>> outer + 1
   2
            """,
        ),
    ),
    (
        "nested-in-list-items",
        textwrap.dedent(
            """
Title
=====

- First item:

  >>> counted = 1

- Second item:

  >>> counted + 1
  2
            """,
        ),
    ),
]


@pytest.mark.parametrize(
    ("test_id", "page"),
    OUT_OF_ORDER_LINES_REST,
    ids=[test_id for test_id, _ in OUT_OF_ORDER_LINES_REST],
)
def test_a_nested_block_collects(
    tmp_path: pathlib.Path,
    test_id: str,
    page: str,
) -> None:
    """A doctest block nested in another node is collected, not fatal.

    docutils leaves ``line`` unset on a block inside a directive, a list item,
    or a block quote, and reading it as a number took the whole page down.
    """
    page_path = tmp_path / "page.rst"
    page_path.write_text(page, encoding="utf-8")

    tests = doctest_docutils.DocutilsDocTestFinder().find(page, str(page_path))

    linenos = [test.lineno or 0 for test in tests]

    assert linenos == sorted(linenos)
    assert all(lineno > 0 for lineno in linenos)


class SkipifFixture(t.NamedTuple):
    """Directive whose ``:skipif:`` decides whether its block runs.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    expression : str
        Expression written on the directive's ``:skipif:`` option.
    skipped : bool
        Whether the block is expected to carry ``SKIP``.
    """

    test_id: str
    expression: str
    skipped: bool


SKIPIF_FIXTURES = [
    SkipifFixture(test_id="true-skips-the-block", expression="True", skipped=True),
    SkipifFixture(test_id="false-runs-the-block", expression="False", skipped=False),
    SkipifFixture(
        test_id="expression-sees-the-starting-globals",
        expression="__name__ == 'nonesuch'",
        skipped=False,
    ),
    SkipifFixture(
        test_id="expression-sees-sys",
        expression="sys.version_info < (3, 10)",
        skipped=False,
    ),
]


@pytest.mark.parametrize(
    SkipifFixture._fields,
    SKIPIF_FIXTURES,
    ids=[f.test_id for f in SKIPIF_FIXTURES],
)
def test_skipif_marks_its_block_skip(
    test_id: str,
    expression: str,
    skipped: bool,
) -> None:
    """A true ``:skipif:`` marks its block ``SKIP`` rather than dropping it.

    Both spellings of "do not run this" land on the same flag, so the block
    stays collectable, countable, and selectable by node id either way.
    """
    page = f".. doctest::\n    :skipif: {expression}\n\n    >>> 2 + 2\n    4\n"

    (test,) = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert test.examples[0].options.get(doctest.SKIP, False) is skipped


GATED_MIDDLE_BLOCK_REST = textwrap.dedent(
    """
    .. doctest:: intro

        >>> greeting = "hello"

    .. doctest:: intro
        :skipif: True

        >>> raise AssertionError("the skipped block ran")

    .. doctest:: intro

        >>> greeting.upper()
        'HELLO'
    """,
)


def test_skipif_skips_only_its_own_block_of_a_group() -> None:
    """A group's other blocks keep running when one of them is skipped.

    The gated block binds nothing its group could read, so it comes back on
    its own rather than merged into a group that runs without it. What is
    left of the group carries no flag, and the block that does still holds
    the source it would have run.
    """
    group, gated = doctest_docutils.DocutilsDocTestFinder().find(
        GATED_MIDDLE_BLOCK_REST,
        "page.rst",
    )

    assert [test.name for test in (group, gated)] == ["intro", "intro[1]"]
    assert [example.options.get(doctest.SKIP, False) for example in group.examples] == [
        False,
        False,
    ]
    assert [example.options[doctest.SKIP] for example in gated.examples] == [True]


def test_lifting_a_gated_block_moves_no_reported_line() -> None:
    """Every example reports the line it reports with the gate turned off.

    The lifted block is positioned where docutils put it, so a reader told it
    was skipped is pointed at the same place the group would have pointed.
    """
    finder = doctest_docutils.DocutilsDocTestFinder()

    def reported(page: str) -> list[int]:
        return sorted(
            (test.lineno or 0) + example.lineno + 1
            for test in finder.find(page, "page.rst")
            for example in test.examples
        )

    assert reported(GATED_MIDDLE_BLOCK_REST) == reported(
        GATED_MIDDLE_BLOCK_REST.replace(":skipif: True", ":skipif: False"),
    )


class GateSpellingFixture(t.NamedTuple):
    """One way of writing "do not run this block", and the block it writes.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    block : str
        Middle block of a three-block group, gated its own way.
    """

    test_id: str
    block: str


GATE_SPELLING_FIXTURES = [
    GateSpellingFixture(
        test_id="skipif-condition",
        block=".. doctest:: intro\n    :skipif: True\n\n    >>> 1 / 0\n",
    ),
    GateSpellingFixture(
        test_id="directive-options-flag",
        block=".. doctest:: intro\n    :options: +SKIP\n\n    >>> 1 / 0\n",
    ),
    GateSpellingFixture(
        test_id="inline-flag",
        block=".. doctest:: intro\n\n    >>> 1 / 0  # doctest: +SKIP\n",
    ),
    GateSpellingFixture(
        test_id="every-example-inline",
        block=(
            ".. doctest:: intro\n\n    >>> 1 / 0  # doctest: +SKIP\n"
            "    >>> 2 / 0  # doctest: +SKIP\n"
        ),
    ),
]


@pytest.mark.parametrize(
    GateSpellingFixture._fields,
    GATE_SPELLING_FIXTURES,
    ids=[f.test_id for f in GATE_SPELLING_FIXTURES],
)
def test_every_spelling_of_a_gate_lifts_its_block_out(
    test_id: str,
    block: str,
) -> None:
    """A block is lifted out for what its examples carry, not how it says it.

    A condition, a directive flag, and an inline comment all land on
    :data:`doctest.SKIP`, so a reader who knows one can predict the others.
    """
    page = (
        ".. doctest:: intro\n\n    >>> greeting = 'hello'\n\n"
        f"{block}\n"
        ".. doctest:: intro\n\n    >>> greeting.upper()\n    'HELLO'\n"
    )

    group, gated = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")
    runner = doctest.DocTestRunner(verbose=False)
    for test in (group, gated):
        runner.run(test, out=lambda _: None)

    assert [test.name for test in (group, gated)] == ["intro", "intro[1]"]
    assert runner.failures == 0


def test_a_half_gated_block_stays_in_its_namespace() -> None:
    """A block with one example left to run is not a skipped block.

    Its silence is the silence pytest keeps for any partly skipped item, and
    the example that runs may bind a name the rest of the group reads.
    """
    page = (
        ".. doctest:: intro\n\n"
        "    >>> greeting = 'hello'  # doctest: +SKIP\n"
        "    >>> greeting = 'hi'\n\n"
        ".. doctest:: intro\n\n    >>> greeting\n    'hi'\n"
    )

    tests = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")
    runner = doctest.DocTestRunner(verbose=False)
    for test in tests:
        runner.run(test, out=lambda _: None)

    assert [test.name for test in tests] == ["intro"]
    assert runner.failures == 0


def test_a_namespace_gated_end_to_end_stays_whole() -> None:
    """A namespace with nothing left to run keeps every block it holds.

    One test reports the skip once. Lifting each block out would report the
    same page N times, which is noise, not information.
    """
    page = (
        ".. doctest:: solo\n    :skipif: True\n\n    >>> 1 / 0\n\n"
        ".. doctest:: solo\n    :options: +SKIP\n\n    >>> 2 / 0\n"
    )

    tests = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert [test.name for test in tests] == ["solo"]
    assert all(
        example.options[doctest.SKIP] for test in tests for example in test.examples
    )


def test_a_shared_page_names_a_gated_block_as_block_scope_does() -> None:
    """The node id that selects a gated block does not move with the scope.

    Under ``document`` the page is one namespace named for the page, so a
    block lifted back out of it lands on the name it carries when every block
    keeps its own namespace.
    """
    page = textwrap.dedent(
        """
        ```python
        >>> value = 1
        ```

        ```python
        >>> value = 999  # doctest: +SKIP
        ```

        ```python
        >>> value
        1
        ```
        """,
    )

    shared = doctest_docutils.DocutilsDocTestFinder(namespace_scope="document")
    apart = doctest_docutils.DocutilsDocTestFinder(namespace_scope="block")

    assert [test.name for test in shared.find(page, "page.md")] == [
        "page.md",
        "page.md[1]",
    ]
    assert [test.name for test in apart.find(page, "page.md")] == [
        "page.md[0]",
        "page.md[1]",
        "page.md[2]",
    ]


def test_an_inline_flag_cannot_reopen_a_true_skipif() -> None:
    """An example's own ``-SKIP`` loses to a condition, unlike to ``:options:``.

    ``sphinx.ext.doctest`` drops a gated block before its source is read, so
    nothing written inside one can turn the gate off. An example that could
    would run on exactly the interpreter or platform it was guarded against.
    """
    page = ".. doctest::\n    :skipif: True\n\n    >>> 2 + 2  # doctest: -SKIP\n    4\n"

    (test,) = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert test.examples[0].options[doctest.SKIP] is True


SKIPPED_SETUP_DIRECTIVES = [
    ("testsetup", "testsetup"),
    ("testcleanup", "testcleanup"),
]


@pytest.mark.parametrize(
    ("test_id", "directive"),
    SKIPPED_SETUP_DIRECTIVES,
    ids=[test_id for test_id, _ in SKIPPED_SETUP_DIRECTIVES],
)
def test_skipif_marks_setup_and_cleanup_blocks_skip(
    test_id: str,
    directive: str,
) -> None:
    """``:skipif:`` reaches the setup and cleanup directives that declare it.

    Both list ``skipif`` in their ``option_spec``, so the option is not a
    ``.. doctest::`` exclusive and has to behave the same on all three. A
    gated one comes back on its own, as any gated block does, so a group whose
    setup never ran says so.
    """
    page = (
        f".. {directive}:: fixture\n    :skipif: True\n\n"
        "    >>> raise AssertionError('the skipped block ran')\n\n"
        ".. doctest:: fixture\n\n    >>> 2 + 2\n    4\n"
    )

    gated, group = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert [test.name for test in (gated, group)] == ["fixture[0]", "fixture"]
    assert [example.options.get(doctest.SKIP, False) for example in group.examples] == [
        False,
    ]
    assert [example.options[doctest.SKIP] for example in gated.examples] == [True]


SKIPIF_STANDALONE_PAGE = textwrap.dedent(
    """
    Standalone
    ==========

    .. doctest::
        :skipif: True

        >>> 1 / 0

    .. doctest::

        >>> 2 + 2
        4
    """,
)


def test_skipif_under_testdocutils(tmp_path: pathlib.Path) -> None:
    """The standalone runner skips the block instead of never seeing it.

    :class:`doctest.DocTestRunner` honours ``SKIP`` itself, so the library
    stays usable without pytest and the skipped example is never executed.
    """
    page = tmp_path / "page.rst"
    page.write_text(SKIPIF_STANDALONE_PAGE, encoding="utf-8")

    results = doctest_docutils.testdocutils(
        str(page),
        module_relative=False,
        report=False,
    )

    assert results.failed == 0


class StandaloneExitFixture(t.NamedTuple):
    """Page run through the ``python -m doctest_docutils`` entry point.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    page : str
        reStructuredText source written to the temporary page.
    exit_code : int
        Status ``doctest_docutils._test`` is expected to return.
    """

    test_id: str
    page: str
    exit_code: int


STANDALONE_EXIT_FIXTURES = [
    StandaloneExitFixture(
        test_id="a-skipped-block-alone-passes",
        page=SKIPIF_STANDALONE_PAGE,
        exit_code=0,
    ),
    StandaloneExitFixture(
        test_id="a-real-failure-beside-it-still-fails",
        page=SKIPIF_STANDALONE_PAGE.replace(
            "    >>> 2 + 2\n    4\n", "    >>> 2 + 2\n    5\n"
        ),
        exit_code=1,
    ),
]


@pytest.mark.parametrize(
    StandaloneExitFixture._fields,
    STANDALONE_EXIT_FIXTURES,
    ids=[f.test_id for f in STANDALONE_EXIT_FIXTURES],
)
def test_skipif_exit_code_from_the_command(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    test_id: str,
    page: str,
    exit_code: int,
) -> None:
    """``python -m doctest_docutils`` exits non-zero only on a real failure."""
    page_path = tmp_path / "page.rst"
    page_path.write_text(page, encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["doctest_docutils", str(page_path)])

    assert doctest_docutils._test() == exit_code

    assert "ZeroDivisionError" not in capsys.readouterr().out


def test_skipif_that_cannot_be_evaluated_names_its_block() -> None:
    """An expression naming something out of reach reports as that block.

    The namespace a ``:skipif:`` sees is small on purpose, so reaching outside
    it is an ordinary mistake; the report has to say which block to go fix.
    """
    page = (
        "Title\n=====\n\n.. doctest::\n"
        '    :skipif: platform.system() == "Windows"\n\n    >>> 2 + 2\n    4\n'
    )

    with pytest.raises(doctest_docutils.SkipifExpressionError) as excinfo:
        doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert str(excinfo.value) == (
        "page.rst:4: :skipif: 'platform.system() == \"Windows\"' failed: "
        "name 'platform' is not defined"
    )


def test_hide_optionflag_parses_without_pytest() -> None:
    """``+HIDE`` parses wherever :mod:`doctest_docutils` is imported.

    The flag is gp-libs' own, and a page carrying an unregistered name fails to
    parse, so registering it only as pytest configures left the standalone
    ``python -m doctest_docutils`` command unable to read the repo's own pages.
    """
    page = (
        ".. doctest::\n\n    >>> base = 40  # doctest: +HIDE\n"
        "    >>> base + 2\n    42\n"
    )

    (test,) = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert test.examples[0].options[doctest_docutils._HIDE_FLAG] is True


STATE_MD = textwrap.dedent(
    """
# Title

```python
>>> greeting = "hello"
>>> greeting
'hello'
```

Narrative prose between the two blocks.

```python
>>> greeting.upper()
'HELLO'
```
    """,
)

SHARED_GROUP_REST = textwrap.dedent(
    """
Title
=====

.. doctest:: intro

    >>> greeting = "hello"

Narrative prose.

.. doctest:: intro

    >>> greeting.upper()
    'HELLO'
    """,
)

DISTINCT_GROUPS_REST = textwrap.dedent(
    """
Title
=====

.. doctest:: alpha

    >>> alpha_only = 1

.. doctest:: beta

    >>> alpha_only
    Traceback (most recent call last):
    NameError: name 'alpha_only' is not defined
    """,
)


class NamespaceFixture(t.NamedTuple):
    """Page whose blocks land in one namespace or in several.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    file_name : str
        Page name, whose suffix picks the parser.
    page : str
        Page content.
    namespace_scope : doctest_docutils.NamespaceScope
        Scope the finder is built with.
    test_names : list[str]
        Test names ``find`` returns, in order.
    example_sources : list[list[str]]
        Example sources per returned test, in document order.
    """

    test_id: str
    file_name: str
    page: str
    namespace_scope: doctest_docutils.NamespaceScope
    test_names: list[str]
    example_sources: list[list[str]]


NAMESPACE_FIXTURES = [
    NamespaceFixture(
        test_id="ungrouped-fences-stay-apart-by-default",
        file_name="page.md",
        page=STATE_MD,
        namespace_scope="block",
        test_names=["page.md[0]", "page.md[1]"],
        example_sources=[['greeting = "hello"', "greeting"], ["greeting.upper()"]],
    ),
    NamespaceFixture(
        test_id="ungrouped-fences-share-the-page-under-document",
        file_name="page.md",
        page=STATE_MD,
        namespace_scope="document",
        test_names=["page.md"],
        example_sources=[
            ['greeting = "hello"', "greeting", "greeting.upper()"],
        ],
    ),
    NamespaceFixture(
        test_id="group-shares-by-default",
        file_name="page.rst",
        page=SHARED_GROUP_REST,
        namespace_scope="block",
        test_names=["intro"],
        example_sources=[['greeting = "hello"', "greeting.upper()"]],
    ),
    NamespaceFixture(
        test_id="group-shares-under-document",
        file_name="page.rst",
        page=SHARED_GROUP_REST,
        namespace_scope="document",
        test_names=["intro"],
        example_sources=[['greeting = "hello"', "greeting.upper()"]],
    ),
    NamespaceFixture(
        test_id="distinct-groups-partition-the-page",
        file_name="page.rst",
        page=DISTINCT_GROUPS_REST,
        namespace_scope="document",
        test_names=["alpha", "beta"],
        example_sources=[["alpha_only = 1"], ["alpha_only"]],
    ),
]


@pytest.mark.parametrize(
    NamespaceFixture._fields,
    NAMESPACE_FIXTURES,
    ids=[f.test_id for f in NAMESPACE_FIXTURES],
)
def test_finder_merges_a_namespace_into_one_test(
    tmp_path: pathlib.Path,
    test_id: str,
    file_name: str,
    page: str,
    namespace_scope: doctest_docutils.NamespaceScope,
    test_names: list[str],
    example_sources: list[list[str]],
) -> None:
    """A namespace is one test holding its blocks' examples in document order.

    Naming a group is the author asking two blocks to share, so a group shares
    at every scope; blocks that name none follow the scope.
    """
    page_path = tmp_path / file_name
    page_path.write_text(page, encoding="utf-8")

    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope=namespace_scope)
    tests = finder.find(page, str(page_path))

    assert [test.name for test in tests] == test_names
    assert [
        [example.source.strip() for example in test.examples] for test in tests
    ] == example_sources


class NamespaceStateFixture(t.NamedTuple):
    """Page run end to end, counting the examples that fail.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    file_name : str
        Page name, whose suffix picks the parser.
    page : str
        Page content.
    namespace_scope : doctest_docutils.NamespaceScope
        Scope the finder is built with.
    failures : int
        Examples expected to fail once every test has run.
    """

    test_id: str
    file_name: str
    page: str
    namespace_scope: doctest_docutils.NamespaceScope
    failures: int


NAMESPACE_STATE_FIXTURES = [
    NamespaceStateFixture(
        test_id="second-fence-cannot-read-the-first-by-default",
        file_name="page.md",
        page=STATE_MD,
        namespace_scope="block",
        failures=1,
    ),
    NamespaceStateFixture(
        test_id="second-fence-reads-the-first-under-document",
        file_name="page.md",
        page=STATE_MD,
        namespace_scope="document",
        failures=0,
    ),
    NamespaceStateFixture(
        test_id="group-reads-what-its-first-block-bound",
        file_name="page.rst",
        page=SHARED_GROUP_REST,
        namespace_scope="block",
        failures=0,
    ),
    NamespaceStateFixture(
        test_id="groups-stay-isolated-from-each-other",
        file_name="page.rst",
        page=DISTINCT_GROUPS_REST,
        namespace_scope="document",
        failures=0,
    ),
]


@pytest.mark.parametrize(
    NamespaceStateFixture._fields,
    NAMESPACE_STATE_FIXTURES,
    ids=[f.test_id for f in NAMESPACE_STATE_FIXTURES],
)
def test_namespace_scope_decides_what_a_block_can_read(
    tmp_path: pathlib.Path,
    test_id: str,
    file_name: str,
    page: str,
    namespace_scope: doctest_docutils.NamespaceScope,
    failures: int,
) -> None:
    """State reaches exactly as far as the namespace it was bound in.

    The isolated page proves it by expecting the ``NameError`` its own examples
    document.
    """
    page_path = tmp_path / file_name
    page_path.write_text(page, encoding="utf-8")

    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope=namespace_scope)
    runner = doctest.DocTestRunner(verbose=False)
    for test in finder.find(page, str(page_path)):
        runner.run(test, out=lambda _: None)

    assert runner.failures == failures


class MergedLineNumberFixture(t.NamedTuple):
    """Page a namespace merges, in each block form docutils positions apart.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    file_name : str
        Page name, whose suffix picks the parser.
    page : str
        Page content.
    """

    test_id: str
    file_name: str
    page: str


LONG_THEN_SHORT_REST = textwrap.dedent(
    """
Title
=====

>>> first = 1
>>> second = 2
>>> third = 3
>>> fourth = 4

Prose short enough that placing by ``node.line`` would overlap the blocks.

>>> first + fourth
5
    """,
)

MERGED_LINE_NUMBER_FIXTURES = [
    MergedLineNumberFixture(
        test_id="MyST-fences",
        file_name="page.md",
        page=STATE_MD,
    ),
    MergedLineNumberFixture(
        test_id="reST-doctest_directives",
        file_name="page.rst",
        page=SHARED_GROUP_REST,
    ),
    MergedLineNumberFixture(
        test_id="reST-doctest_blocks",
        file_name="page.rst",
        page=LONG_THEN_SHORT_REST,
    ),
]


@pytest.mark.parametrize(
    MergedLineNumberFixture._fields,
    MERGED_LINE_NUMBER_FIXTURES,
    ids=[f.test_id for f in MERGED_LINE_NUMBER_FIXTURES],
)
def test_merged_examples_keep_their_gutter(
    tmp_path: pathlib.Path,
    test_id: str,
    file_name: str,
    page: str,
) -> None:
    """The line a failure prints is the line the failing prompt sits on.

    pytest counts the ``%03d`` gutter from ``test.lineno + 1`` through the
    merged source, so the blank lines standing in for prose have to match the
    prose they replace, block after block.
    """
    page_path = tmp_path / file_name
    page_path.write_text(page, encoding="utf-8")

    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope="document")
    (merged,) = finder.find(page, str(page_path))

    gutter = (merged.docstring or "").splitlines()
    assert [gutter[example.lineno] for example in merged.examples] == [
        f">>> {example.source.splitlines()[0]}" for example in merged.examples
    ]


def _reported_lines(
    page: str,
    page_path: pathlib.Path,
    scope: doctest_docutils.NamespaceScope,
) -> list[int]:
    """Return the file line every example on `page` reports, at `scope`."""
    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope=scope)
    return [
        (test.lineno or 0) + example.lineno + 1
        for test in finder.find(page, str(page_path))
        for example in test.examples
    ]


@pytest.mark.parametrize(
    ("test_id", "file_name", "page"),
    [
        ("MyST-fences", "page.md", STATE_MD),
        ("reST-doctest_directives", "page.rst", SHARED_GROUP_REST),
        ("reST-doctest_blocks", "page.rst", LONG_THEN_SHORT_REST),
    ],
    ids=["MyST-fences", "reST-doctest_directives", "reST-doctest_blocks"],
)
def test_merging_moves_no_reported_line(
    tmp_path: pathlib.Path,
    test_id: str,
    file_name: str,
    page: str,
) -> None:
    """A merged example reports the line it reports on its own.

    Every block form is placed at the line docutils gave it, so a page whose
    blocks stand clear of each other reads the same merged as it does apart.
    """
    page_path = tmp_path / file_name
    page_path.write_text(page, encoding="utf-8")

    assert _reported_lines(page, page_path, "document") == _reported_lines(
        page,
        page_path,
        "block",
    )


CROWDED_REST = textwrap.dedent(
    """
Title
=====

>>> one = 1
>>> two = 2
>>> three = 3
>>> four = 4
>>> five = 5
>>> six = 6

Prose.

.. doctest::

    >>> one + six
    7
    """,
)


def test_a_crowded_block_follows_the_one_above_it(tmp_path: pathlib.Path) -> None:
    """A block the lines above already reach reports further down the page.

    docutils reports a reStructuredText doctest block's *last* line, so its own
    examples already report lines below the block: a six-line block starting on
    line 5 reports lines 10 to 15. A directive two lines further down has to
    follow those, and moves by the overlap. The gutter still shows the failing
    prompt, which is what a reader reads the report for.
    """
    page_path = tmp_path / "page.rst"
    page_path.write_text(CROWDED_REST, encoding="utf-8")

    apart = _reported_lines(CROWDED_REST, page_path, "block")
    merged = _reported_lines(CROWDED_REST, page_path, "document")

    assert merged[:-1] == apart[:-1]
    assert merged[-1] - apart[-1] == 2

    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope="document")
    (test,) = finder.find(CROWDED_REST, str(page_path))
    gutter = (test.docstring or "").splitlines()
    assert gutter[test.examples[-1].lineno] == ">>> one + six"


@pytest.mark.parametrize(
    ("test_id", "page"),
    OUT_OF_ORDER_LINES_REST,
    ids=[test_id for test_id, _ in OUT_OF_ORDER_LINES_REST],
)
def test_merging_survives_a_block_docutils_left_unpositioned(
    tmp_path: pathlib.Path,
    test_id: str,
    page: str,
) -> None:
    """A doctest block nested in another node still merges and runs.

    docutils leaves ``line`` unset on a block inside a directive, a list item,
    or a block quote, so placing every block by that value alone would stack
    them all at the top of the page.
    """
    page_path = tmp_path / "page.rst"
    page_path.write_text(page, encoding="utf-8")

    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope="document")
    (merged,) = finder.find(page, str(page_path))
    runner = doctest.DocTestRunner(verbose=False)
    runner.run(merged, out=lambda _: None)

    linenos = [example.lineno for example in merged.examples]
    assert linenos == sorted(set(linenos))
    assert runner.failures == 0


def test_a_group_survives_an_include(tmp_path: pathlib.Path) -> None:
    """A group split across an ``.. include::`` merges and runs.

    docutils numbers the included page's nodes against that page, so the second
    block claims a line the first one already covers.
    """
    (tmp_path / "part.rst").write_text(
        "Part\n----\n\nProse.\n\n.. doctest:: intro\n\n"
        "    >>> greeting.upper()\n    'HELLO'\n",
        encoding="utf-8",
    )
    page = (
        "Title\n=====\n\n.. doctest:: intro\n\n"
        "    >>> greeting = 'hello'\n\n.. include:: part.rst\n"
    )
    page_path = tmp_path / "main.rst"
    page_path.write_text(page, encoding="utf-8")

    finder = doctest_docutils.DocutilsDocTestFinder()
    (merged,) = finder.find(page, str(page_path))
    runner = doctest.DocTestRunner(verbose=False)
    runner.run(merged, out=lambda _: None)

    assert [example.source.strip() for example in merged.examples] == [
        "greeting = 'hello'",
        "greeting.upper()",
    ]
    assert runner.failures == 0


def test_markdown_failures_point_at_the_prompt(tmp_path: pathlib.Path) -> None:
    """A merged Markdown page reports the file line each ``>>>`` sits on."""
    page_path = tmp_path / "page.md"
    page_path.write_text(STATE_MD, encoding="utf-8")

    finder = doctest_docutils.DocutilsDocTestFinder(namespace_scope="document")
    (test,) = finder.find(STATE_MD, str(page_path))

    lines = STATE_MD.splitlines()
    reported = [(test.lineno or 0) + example.lineno + 1 for example in test.examples]
    assert [lines[lineno - 1] for lineno in reported] == [
        '>>> greeting = "hello"',
        ">>> greeting",
        ">>> greeting.upper()",
    ]


def test_collection_logs_the_namespace_each_block_joined(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Collection records the namespace, source file, and block type.

    ``doctest_source_file`` and ``doctest_block_type`` are the structured keys
    a log processor filters on, so assert the schema, not the message.
    """
    finder = doctest_docutils.DocutilsDocTestFinder()
    with caplog.at_level(logging.DEBUG, logger="doctest_docutils"):
        finder.find(SHARED_GROUP_REST, "page.rst")

    collected = [
        record
        for record in caplog.records
        if record.msg == "doctest block collected into namespace %s"
    ]
    assert [record.args for record in collected] == [("intro",), ("intro",)]
    assert {record.__dict__["doctest_block_type"] for record in collected} == {
        "doctest",
    }
    assert {record.__dict__["doctest_source_file"] for record in collected} == {
        "page.rst",
    }


def test_namespace_scope_rejects_an_unknown_name() -> None:
    """An unknown scope names the values it could have been."""
    with pytest.raises(doctest_docutils.NamespaceScopeError) as excinfo:
        doctest_docutils.DocutilsDocTestFinder(
            namespace_scope=t.cast("doctest_docutils.NamespaceScope", "per-file"),
        )

    assert str(excinfo.value) == (
        "Unknown namespace scope: 'per-file'. Expected one of: block, document"
    )


class PyversionFixture(t.NamedTuple):
    """Directive whose ``:pyversion:`` decides whether its block runs.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    spec : str
        PEP-440 specifier written on the ``:pyversion:`` option.
    skipped : bool
        Whether the block is expected to carry ``SKIP``.
    """

    test_id: str
    spec: str
    skipped: bool


PYVERSION_FIXTURES = [
    PyversionFixture(test_id="satisfied-runs", spec=">=3.10", skipped=False),
    PyversionFixture(test_id="unsatisfied-skips", spec=">=99.0", skipped=True),
    PyversionFixture(test_id="upper-bound-skips", spec="<3.0", skipped=True),
]


@pytest.mark.parametrize(
    PyversionFixture._fields,
    PYVERSION_FIXTURES,
    ids=[f.test_id for f in PYVERSION_FIXTURES],
)
def test_pyversion_skips_the_block_it_excludes(
    test_id: str,
    spec: str,
    skipped: bool,
) -> None:
    """``:pyversion:`` compares the running interpreter against the specifier.

    The arguments were reversed, so every specifier was parsed as a version and
    the page died on ``InvalidVersion`` before the option could decide anything.
    """
    page = f".. doctest::\n    :pyversion: {spec}\n\n    >>> 2 + 2\n    4\n"

    (test,) = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert test.examples[0].options.get(doctest.SKIP, False) is skipped


BLANKLINE_REST = textwrap.dedent(
    """
Title
=====

.. doctest::

   >>> print("a\\n\\nb")
   a
   <BLANKLINE>
   b
    """,
)

SETUP_GROUP_REST = textwrap.dedent(
    """
Title
=====

.. testsetup:: demo

   >>> import math

.. doctest:: demo

   >>> math.floor(2.5)
   2

.. testcleanup:: demo

   >>> del math
    """,
)


class DirectiveSourceFixture(t.NamedTuple):
    """Page whose blocks only run once the directive's own source is read.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    page : str
        reStructuredText page.
    collected : int
        Tests expected back from the finder.
    """

    test_id: str
    page: str
    collected: int


DIRECTIVE_SOURCE_FIXTURES = [
    DirectiveSourceFixture(
        test_id="blankline-marker-inside-a-directive",
        page=BLANKLINE_REST,
        collected=1,
    ),
    DirectiveSourceFixture(
        test_id="testsetup-and-testcleanup-share-a-group",
        page=SETUP_GROUP_REST,
        collected=1,
    ),
]


@pytest.mark.parametrize(
    DirectiveSourceFixture._fields,
    DIRECTIVE_SOURCE_FIXTURES,
    ids=[f.test_id for f in DIRECTIVE_SOURCE_FIXTURES],
)
def test_directive_blocks_run_from_their_own_source(
    test_id: str,
    page: str,
    collected: int,
) -> None:
    """Directives run the source they stored, not the code they render.

    ``.. doctest::`` rewrites a ``<BLANKLINE>`` marker into a real blank line
    for the page and keeps the marker on the node, so reading the rendered
    text instead compared against a blank line and failed. A ``testsetup``
    naming a group is only useful once that group is one namespace.
    """
    tests = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")
    runner = doctest.DocTestRunner(verbose=False)
    for test in tests:
        runner.run(test, out=lambda _: None)

    assert len(tests) == collected
    assert runner.failures == 0


def test_a_failing_block_still_fails_beside_a_skipped_one() -> None:
    """Skipping one block of a group does not excuse the rest of it.

    Lifting the gated block out must not lift the group's coverage out with
    it: a skip that quietly took the whole namespace along would turn a broken
    page green.
    """
    page = textwrap.dedent(
        """
Title
=====

.. doctest:: demo
    :skipif: True

    >>> 1 / 0

.. doctest:: demo

    >>> 2 + 2
    5
        """,
    )

    tests = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")
    runner = doctest.DocTestRunner(verbose=False)
    for test in tests:
        runner.run(test, out=lambda _: None)

    assert [test.name for test in tests] == ["demo[0]", "demo"]
    assert runner.failures == 1


def test_a_skipped_block_must_still_parse() -> None:
    """A skipped block is parsed, so malformed doctest source still reports.

    Dropping the block hid its syntax; marking it ``SKIP`` does not. That
    matches ``:options: +SKIP``, whose blocks have always had to parse.
    """
    page = ".. doctest::\n    :skipif: True\n\n    >>>print(2)\n"

    with pytest.raises(ValueError, match="lacks blank after >>>"):
        doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")


OUT_OF_ORDER_PHASES_REST = textwrap.dedent(
    """
Title
=====

.. testcleanup:: demo

   >>> del value

.. doctest:: demo

   >>> value
   1

.. testsetup:: demo

   >>> value = 1
    """,
)

TWO_SETUPS_REST = textwrap.dedent(
    """
Title
=====

.. testsetup:: demo

   >>> order = ["first"]

.. testsetup:: demo

   >>> order.append("second")

.. doctest:: demo

   >>> order
   ['first', 'second']
    """,
)


def test_a_group_runs_setup_first_and_cleanup_last() -> None:
    """Phase beats page order, so a hidden block can sit anywhere.

    ``testsetup`` and ``testcleanup`` render as comments, so an author moves
    them out of the reader's way; running them where they sit bound names too
    late and tore them down too early.
    """
    (test,) = doctest_docutils.DocutilsDocTestFinder().find(
        OUT_OF_ORDER_PHASES_REST,
        "page.rst",
    )
    runner = doctest.DocTestRunner(verbose=False)
    runner.run(test, out=lambda _: None)

    assert [example.source.strip() for example in test.examples] == [
        "value = 1",
        "value",
        "del value",
    ]
    assert runner.failures == 0


def test_two_setups_keep_their_page_order() -> None:
    """Blocks of one phase run in the order the page wrote them."""
    (test,) = doctest_docutils.DocutilsDocTestFinder().find(
        TWO_SETUPS_REST,
        "page.rst",
    )
    runner = doctest.DocTestRunner(verbose=False)
    runner.run(test, out=lambda _: None)

    assert runner.failures == 0


COMMA_GROUPS_REST = textwrap.dedent(
    """
Title
=====

.. doctest:: alpha, beta

   >>> shared = 1

.. doctest:: beta

   >>> shared
   1
    """,
)

WILDCARD_GROUP_REST = textwrap.dedent(
    """
Title
=====

.. testsetup:: *

   >>> import math

.. doctest:: alpha

   >>> math.floor(2.5)
   2

.. doctest:: beta

   >>> math.ceil(2.5)
   3
    """,
)


def test_a_block_joins_every_group_it_names() -> None:
    """A comma list is every group the block belongs to, not just the first."""
    tests = doctest_docutils.DocutilsDocTestFinder().find(
        COMMA_GROUPS_REST,
        "page.rst",
    )
    runner = doctest.DocTestRunner(verbose=False)
    for test in tests:
        runner.run(test, out=lambda _: None)

    assert [(test.name, len(test.examples)) for test in tests] == [
        ("alpha", 1),
        ("beta", 2),
    ]
    assert runner.failures == 0


def test_a_wildcard_joins_every_group_the_page_declares() -> None:
    """``*`` is how a page writes one setup block for all of its groups."""
    tests = doctest_docutils.DocutilsDocTestFinder().find(
        WILDCARD_GROUP_REST,
        "page.rst",
    )
    runner = doctest.DocTestRunner(verbose=False)
    for test in tests:
        runner.run(test, out=lambda _: None)

    assert [test.name for test in tests] == ["alpha", "beta"]
    assert all(len(test.examples) == 2 for test in tests)
    assert runner.failures == 0


def test_a_shared_block_reports_one_line_in_every_group() -> None:
    """Merging shifts example line numbers in place, so each copy is its own.

    A block joining two namespaces that shared its examples would have them
    shifted twice, and the second group would report failures against a line
    the block does not sit on.
    """
    alpha, beta = doctest_docutils.DocutilsDocTestFinder().find(
        COMMA_GROUPS_REST,
        "page.rst",
    )

    def reported(test: doctest.DocTest, index: int) -> int:
        return (test.lineno or 0) + test.examples[index].lineno + 1

    assert reported(alpha, 0) == reported(beta, 0)


def test_out_of_order_phases_report_their_own_lines() -> None:
    """A phase written away from its group still reports where it sits.

    A namespace hands its blocks over as setup, tests, cleanup, which is
    rarely page order. Anchoring the merged text on that sequence reported
    every example against whichever block came first in it, and could point
    past the end of the file.
    """
    finder = doctest_docutils.DocutilsDocTestFinder()

    def reported(page: str) -> list[tuple[str, int]]:
        # Pairs rather than a dict keyed on the source: two examples can share
        # a source, and one would then overwrite the other's line silently.
        # Sorted because a merged namespace hands its blocks over in phase
        # order and three separate ones come back in page order.
        return sorted(
            (example.source.strip(), (test.lineno or 0) + example.lineno + 1)
            for test in finder.find(page, "page.rst")
            for example in test.examples
        )

    merged = reported(OUT_OF_ORDER_PHASES_REST)
    alone = reported(OUT_OF_ORDER_PHASES_REST.replace(":: demo", "::"))

    assert merged == alone
    assert max(line for _, line in merged) <= len(
        OUT_OF_ORDER_PHASES_REST.splitlines(),
    )
