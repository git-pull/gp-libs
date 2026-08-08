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


def test_finder_keeps_stock_per_block_results() -> None:
    """The compatibility finder returns independent stock doctest objects."""
    source = """.. testsetup:: shared

   value = 40

.. doctest:: shared

   >>> value + 2
   42

.. testcleanup:: shared

   del value
"""

    tests = doctest_docutils.DocutilsDocTestFinder().find(source, "guide.rst")

    assert len(tests) == 3
    assert all(type(test) is doctest.DocTest for test in tests)
    assert len({id(test.globs) for test in tests}) == 3


def test_finder_preserves_source_order_past_single_digit_ordinals() -> None:
    """Compatibility results retain source order instead of sorting names."""
    source = "\n".join(f">>> {ordinal}\n{ordinal}\n" for ordinal in range(12))

    tests = doctest_docutils.DocutilsDocTestFinder().find(source, "guide.rst")

    assert [test.name for test in tests] == [
        f"guide.rst[{ordinal}]" for ordinal in range(12)
    ]


def test_finder_preserves_zero_based_line_and_include_source(
    tmp_path: pathlib.Path,
) -> None:
    """Stock finder results report the block's physical source location."""
    included = tmp_path / "included.rst"
    included.write_text(">>> 1 + 1\n3\n", encoding="utf-8")
    root = tmp_path / "guide.rst"
    root.write_text(".. include:: included.rst\n", encoding="utf-8")

    tests = doctest_docutils.DocutilsDocTestFinder().find(
        root.read_text(encoding="utf-8"),
        str(root),
    )

    assert len(tests) == 1
    assert tests[0].filename == str(included)
    assert tests[0].lineno == 0


def test_testdocutils_owns_group_lifecycle(tmp_path: pathlib.Path) -> None:
    """The direct runner shares setup state and cleans up after failure."""
    source_path = tmp_path / "guide.rst"
    source_path.write_text(
        """.. testsetup:: shared

   value = 40

.. doctest:: shared

   >>> value + 2
   99

.. testcleanup:: shared

   cleaned.append(value)
""",
        encoding="utf-8",
    )
    cleaned: list[int] = []

    result = doctest_docutils.testdocutils(
        str(source_path),
        module_relative=False,
        globs={"cleaned": cleaned},
        report=False,
    )

    assert result.failed == 1
    assert result.attempted == 1
    assert cleaned == [40]


def test_testdocutils_retains_report_suppressed_failure_total(
    tmp_path: pathlib.Path,
) -> None:
    """The direct summary count is independent of detailed failure reports."""
    source_path = tmp_path / "guide.rst"
    source_path.write_text(
        ">>> 1 + 1\n3\n>>> 2 + 2\n5\n",
        encoding="utf-8",
    )

    result = doctest_docutils.testdocutils(
        str(source_path),
        module_relative=False,
        report=False,
        optionflags=doctest.REPORT_ONLY_FIRST_FAILURE,
    )

    assert result.failed == 2
    assert result.attempted == 2


def test_testdocutils_returns_modern_skip_statistics(
    tmp_path: pathlib.Path,
) -> None:
    """The direct facade retains CPython's version-shaped skip total."""
    source_path = tmp_path / "guide.rst"
    source_path.write_text(
        ">>> 1 + 1  # doctest: +SKIP\n99\n>>> 2 + 2\n4\n",
        encoding="utf-8",
    )

    result = doctest_docutils.testdocutils(
        str(source_path),
        module_relative=False,
        report=False,
    )

    if hasattr(result, "skipped"):
        assert t.cast(t.Any, result).skipped == 1
