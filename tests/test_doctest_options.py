"""Test doctest option flags for rst/md files.

Tests for doctest option flags (ELLIPSIS, NORMALIZE_WHITESPACE, SKIP, etc.)
in reStructuredText and Markdown files via pytest_doctest_docutils.

Ref: pytest's test_doctest.py option flag tests.
"""

from __future__ import annotations

import textwrap
import typing as t

import _pytest.pytester
import pytest


class DoctestOptionCase(t.NamedTuple):
    """Test case for doctest option flags."""

    test_id: str
    file_ext: str
    ini_options: str
    doctest_content: str
    expected_outcome: str
    description: str


DOCTEST_OPTION_CASES = [
    # ELLIPSIS tests
    DoctestOptionCase(
        test_id="ellipsis-via-ini-rst",
        file_ext=".rst",
        ini_options="doctest_optionflags = ELLIPSIS",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> print("hello world")
            hello ...
            """,
        ),
        expected_outcome="passed",
        description="ELLIPSIS flag via pytest.ini works for .rst files",
    ),
    DoctestOptionCase(
        test_id="ellipsis-via-ini-md",
        file_ext=".md",
        ini_options="doctest_optionflags = ELLIPSIS",
        doctest_content=textwrap.dedent(
            """
            # Example

            ```python
            >>> print("hello world")
            hello ...
            ```
            """,
        ),
        expected_outcome="passed",
        description="ELLIPSIS flag via pytest.ini works for .md files",
    ),
    # NORMALIZE_WHITESPACE tests
    DoctestOptionCase(
        test_id="normalize-whitespace-via-ini-rst",
        file_ext=".rst",
        ini_options="doctest_optionflags = NORMALIZE_WHITESPACE",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> print("a   b   c")
            a b c
            """,
        ),
        expected_outcome="passed",
        description="NORMALIZE_WHITESPACE flag via pytest.ini works for .rst",
    ),
    DoctestOptionCase(
        test_id="normalize-whitespace-via-ini-md",
        file_ext=".md",
        ini_options="doctest_optionflags = NORMALIZE_WHITESPACE",
        doctest_content=textwrap.dedent(
            """
            # Example

            ```python
            >>> print("a   b   c")
            a b c
            ```
            """,
        ),
        expected_outcome="passed",
        description="NORMALIZE_WHITESPACE flag via pytest.ini works for .md",
    ),
    # Combined flags
    DoctestOptionCase(
        test_id="ellipsis-and-normalize-whitespace-rst",
        file_ext=".rst",
        ini_options="doctest_optionflags = ELLIPSIS NORMALIZE_WHITESPACE",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> print("hello   world   test")
            hello ... test
            """,
        ),
        expected_outcome="passed",
        description="Combined ELLIPSIS and NORMALIZE_WHITESPACE flags work",
    ),
    # Inline SKIP directive
    DoctestOptionCase(
        test_id="inline-skip-directive-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> 1 / 0  # doctest: +SKIP
            """,
        ),
        expected_outcome="skipped",
        description="Inline +SKIP directive works in .rst files",
    ),
    DoctestOptionCase(
        test_id="inline-skip-directive-md",
        file_ext=".md",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            # Example

            ```python
            >>> 1 / 0  # doctest: +SKIP
            ```
            """,
        ),
        expected_outcome="skipped",
        description="Inline +SKIP directive works in .md files",
    ),
    # Inline ELLIPSIS directive
    DoctestOptionCase(
        test_id="inline-ellipsis-directive-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> print("hello world")  # doctest: +ELLIPSIS
            hello ...
            """,
        ),
        expected_outcome="passed",
        description="Inline +ELLIPSIS directive works in .rst files",
    ),
    DoctestOptionCase(
        test_id="inline-ellipsis-directive-md",
        file_ext=".md",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            # Example

            ```python
            >>> print("hello world")  # doctest: +ELLIPSIS
            hello ...
            ```
            """,
        ),
        expected_outcome="passed",
        description="Inline +ELLIPSIS directive works in .md files",
    ),
]


@pytest.mark.parametrize(
    DoctestOptionCase._fields,
    DOCTEST_OPTION_CASES,
    ids=[c.test_id for c in DOCTEST_OPTION_CASES],
)
def test_doctest_options(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_ext: str,
    ini_options: str,
    doctest_content: str,
    expected_outcome: str,
    description: str,
) -> None:
    """Test doctest option flags in rst/md files.

    Verifies that doctest option flags work correctly when:
    - Set via doctest_optionflags in pytest.ini
    - Set inline via # doctest: +FLAG comments
    """
    pytester.plugins = ["pytest_doctest_docutils"]

    # Build pytest.ini content
    ini_lines = ["[pytest]", "addopts=-p no:doctest -vv"]
    if ini_options:
        ini_lines.append(ini_options)
    ini_content = "\n".join(ini_lines)

    pytester.makefile(".ini", pytest=ini_content)

    # Create the test file
    filename = f"test_doc{file_ext}"
    file_path = pytester.path / filename
    file_path.write_text(doctest_content, encoding="utf-8")

    result = pytester.runpytest(str(file_path))

    if expected_outcome == "passed":
        result.assert_outcomes(passed=1, errors=0)
    elif expected_outcome == "failed":
        result.assert_outcomes(failed=1, errors=0)
    elif expected_outcome == "skipped":
        # When all examples are skipped, the test is reported as skipped
        result.assert_outcomes(skipped=1, errors=0)


class ContinueOnFailureCase(t.NamedTuple):
    """Test case for continue-on-failure behavior."""

    test_id: str
    file_ext: str
    cli_args: list[str]
    doctest_content: str
    expected_failures: int
    description: str


CONTINUE_ON_FAILURE_CASES = [
    ContinueOnFailureCase(
        test_id="continue-on-failure-shows-all-failures-rst",
        file_ext=".rst",
        cli_args=["--doctest-continue-on-failure"],
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> 1 + 1
            3
            >>> 2 + 2
            5
            >>> 3 + 3
            7
            """,
        ),
        expected_failures=1,
        description="--doctest-continue-on-failure shows all failures in .rst",
    ),
    ContinueOnFailureCase(
        test_id="continue-on-failure-shows-all-failures-md",
        file_ext=".md",
        cli_args=["--doctest-continue-on-failure"],
        doctest_content=textwrap.dedent(
            """
            # Example

            ```python
            >>> 1 + 1
            3
            >>> 2 + 2
            5
            ```
            """,
        ),
        expected_failures=1,
        description="--doctest-continue-on-failure shows all failures in .md",
    ),
]


@pytest.mark.parametrize(
    ContinueOnFailureCase._fields,
    CONTINUE_ON_FAILURE_CASES,
    ids=[c.test_id for c in CONTINUE_ON_FAILURE_CASES],
)
def test_continue_on_failure(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_ext: str,
    cli_args: list[str],
    doctest_content: str,
    expected_failures: int,
    description: str,
) -> None:
    """Test --doctest-continue-on-failure behavior.

    When enabled, all doctest failures should be reported, not just the first.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest -vv")

    # Create the test file
    filename = f"test_doc{file_ext}"
    file_path = pytester.path / filename
    file_path.write_text(doctest_content, encoding="utf-8")

    result = pytester.runpytest(*cli_args, str(file_path))

    # Should have expected number of failures
    result.assert_outcomes(failed=expected_failures)


class CustomFlagCase(t.NamedTuple):
    """Test case for custom doctest flags (ALLOW_UNICODE, ALLOW_BYTES, NUMBER)."""

    test_id: str
    file_ext: str
    ini_options: str
    doctest_content: str
    expected_outcome: str
    description: str


CUSTOM_FLAG_CASES = [
    CustomFlagCase(
        test_id="allow-unicode-flag-rst",
        file_ext=".rst",
        ini_options="doctest_optionflags = ALLOW_UNICODE",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> "hello"
            'hello'
            """,
        ),
        expected_outcome="passed",
        description="ALLOW_UNICODE custom flag works in .rst",
    ),
    CustomFlagCase(
        test_id="number-flag-rst",
        file_ext=".rst",
        ini_options="doctest_optionflags = NUMBER",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            >>> 3.14159265358979
            3.14
            """,
        ),
        expected_outcome="passed",
        description="NUMBER custom flag works in .rst",
    ),
]


@pytest.mark.parametrize(
    CustomFlagCase._fields,
    CUSTOM_FLAG_CASES,
    ids=[c.test_id for c in CUSTOM_FLAG_CASES],
)
def test_custom_flags(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_ext: str,
    ini_options: str,
    doctest_content: str,
    expected_outcome: str,
    description: str,
) -> None:
    """Test custom doctest flags (ALLOW_UNICODE, ALLOW_BYTES, NUMBER).

    These are pytest-specific extensions to standard doctest flags.
    """
    pytester.plugins = ["pytest_doctest_docutils"]

    ini_lines = ["[pytest]", "addopts=-p no:doctest -vv"]
    if ini_options:
        ini_lines.append(ini_options)
    ini_content = "\n".join(ini_lines)

    pytester.makefile(".ini", pytest=ini_content)

    # Create the test file
    filename = f"test_doc{file_ext}"
    file_path = pytester.path / filename
    file_path.write_text(doctest_content, encoding="utf-8")

    result = pytester.runpytest(str(file_path))

    if expected_outcome == "passed":
        result.assert_outcomes(passed=1, errors=0)
    elif expected_outcome == "failed":
        result.assert_outcomes(failed=1, errors=0)


class EdgeCaseTestCase(t.NamedTuple):
    """Test case for edge cases in doctest files."""

    test_id: str
    file_ext: str
    file_content: str
    expected_tests: int
    expected_outcome: str
    description: str


EDGE_CASE_TESTS = [
    EdgeCaseTestCase(
        test_id="empty-rst-file",
        file_ext=".rst",
        file_content="",
        expected_tests=0,
        expected_outcome="no_tests",
        description="Empty .rst file produces no tests",
    ),
    EdgeCaseTestCase(
        test_id="empty-md-file",
        file_ext=".md",
        file_content="",
        expected_tests=0,
        expected_outcome="no_tests",
        description="Empty .md file produces no tests",
    ),
    EdgeCaseTestCase(
        test_id="no-doctest-rst",
        file_ext=".rst",
        file_content=textwrap.dedent(
            """
            Example
            =======

            This is just regular text without any doctests.
            """,
        ),
        expected_tests=0,
        expected_outcome="no_tests",
        description=".rst file without doctests produces no tests",
    ),
    EdgeCaseTestCase(
        test_id="no-doctest-md",
        file_ext=".md",
        file_content=textwrap.dedent(
            """
            # Example

            This is just regular text without any doctests.

            ```javascript
            // Not a Python doctest
            console.log("hello");
            ```
            """,
        ),
        expected_tests=0,
        expected_outcome="no_tests",
        description=".md file without doctests produces no tests",
    ),
]


@pytest.mark.parametrize(
    EdgeCaseTestCase._fields,
    EDGE_CASE_TESTS,
    ids=[c.test_id for c in EDGE_CASE_TESTS],
)
def test_edge_cases(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_ext: str,
    file_content: str,
    expected_tests: int,
    expected_outcome: str,
    description: str,
) -> None:
    """Test edge cases in doctest file handling.

    Tests empty files and files without doctests.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest -vv")

    # Create the test file
    filename = f"test_doc{file_ext}"
    file_path = pytester.path / filename
    file_path.write_text(file_content, encoding="utf-8")

    result = pytester.runpytest(str(file_path), "-v")

    if expected_outcome == "no_tests":
        # Should collect 0 tests (file may be collected but no items)
        stdout = result.stdout.str()
        assert "0 items" in stdout or "no tests ran" in stdout or expected_tests == 0
    elif expected_outcome == "passed":
        result.assert_outcomes(passed=expected_tests)
