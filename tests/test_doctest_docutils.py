"""Tests for doctest_docutils."""

from __future__ import annotations

import doctest
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
    """Directive whose ``:skipif:`` decides if its block is collected.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    expression : str
        Expression written on the directive's ``:skipif:`` option.
    collected : int
        Tests expected back from the page.
    """

    test_id: str
    expression: str
    collected: int


SKIPIF_FIXTURES = [
    SkipifFixture(test_id="true-drops-the-block", expression="True", collected=0),
    SkipifFixture(test_id="false-keeps-the-block", expression="False", collected=1),
    SkipifFixture(
        test_id="expression-sees-the-starting-globals",
        expression="__name__ == 'nonesuch'",
        collected=1,
    ),
    SkipifFixture(
        test_id="expression-sees-sys",
        expression="sys.version_info < (3, 10)",
        collected=1,
    ),
]


@pytest.mark.parametrize(
    SkipifFixture._fields,
    SKIPIF_FIXTURES,
    ids=[f.test_id for f in SKIPIF_FIXTURES],
)
def test_skipif_drops_a_block_before_it_runs(
    test_id: str,
    expression: str,
    collected: int,
) -> None:
    """A true ``:skipif:`` expression drops its block out of collection."""
    page = f".. doctest::\n    :skipif: {expression}\n\n    >>> 2 + 2\n    4\n"

    tests = doctest_docutils.DocutilsDocTestFinder().find(page, "page.rst")

    assert len(tests) == collected


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
