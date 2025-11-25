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
        return super().__init__(f"No file_path_mode supported for {file_path_mode}")


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
