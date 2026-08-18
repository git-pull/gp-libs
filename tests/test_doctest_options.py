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
    DoctestOptionCase(
        test_id="skipif-false-runs-the-block-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::
                :skipif: False

                >>> 2 + 2
                4
            """,
        ),
        expected_outcome="passed",
        description=":skipif: False leaves the block collected",
    ),
    DoctestOptionCase(
        test_id="skipif-true-reports-as-skipped-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::
                :skipif: True

                >>> 1 / 0
            """,
        ),
        expected_outcome="skipped",
        description=":skipif: True reports the same way as :options: +SKIP",
    ),
    DoctestOptionCase(
        test_id="skipif-true-reports-as-skipped-md",
        file_ext=".md",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            # Example

            ```{doctest}
            :skipif: True

            >>> 1 / 0
            ```
            """,
        ),
        expected_outcome="skipped",
        description=":skipif: True reports as skipped in a Markdown fence too",
    ),
    DoctestOptionCase(
        test_id="inline-flag-cannot-reopen-a-true-skipif-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::
                :skipif: True

                >>> 2 + 2  # doctest: -SKIP
                4
            """,
        ),
        expected_outcome="skipped",
        description="An example's own flag cannot reopen a true :skipif:",
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
    DoctestOptionCase(
        test_id="directive-options-normalize-whitespace-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::
                :options: +NORMALIZE_WHITESPACE

                >>> print("a  b")
                a b
            """,
        ),
        expected_outcome="passed",
        description=":options: applies to the block's examples",
    ),
    DoctestOptionCase(
        test_id="directive-options-skip-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::
                :options: +SKIP

                >>> 1 / 0
            """,
        ),
        expected_outcome="skipped",
        description=":options: +SKIP skips the block's examples",
    ),
    DoctestOptionCase(
        test_id="inline-flag-beats-directive-options-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::
                :options: +SKIP

                >>> 2 + 2  # doctest: -SKIP
                4
            """,
        ),
        expected_outcome="passed",
        description="An example's own flag overrides the directive's options",
    ),
    DoctestOptionCase(
        test_id="inline-flag-inside-directive-rst",
        file_ext=".rst",
        ini_options="",
        doctest_content=textwrap.dedent(
            """
            Example
            =======

            .. doctest::

                >>> print("a  b")  # doctest: +NORMALIZE_WHITESPACE
                a b
            """,
        ),
        expected_outcome="passed",
        description="An inline flag applies although the directive trims it",
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


THREE_BLOCK_REST = textwrap.dedent(
    """
    Example
    =======

    .. doctest::
        :skipif: True

        >>> 1 / 0

    .. doctest::
        :options: +SKIP

        >>> 1 / 0

    .. doctest::

        >>> 2 + 2
        4
    """,
)


def test_skipif_true_reports_like_the_skip_flag(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A ``:skipif:`` block collects, counts, and reports as ``+SKIP`` does.

    A page holding all three spellings — a true ``:skipif:``, an
    ``:options: +SKIP``, and an ordinary block — collects three items. The two
    skipped ones report under ``-rs`` with the same reason, so a reader who
    knows either spelling can predict the other.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    page = pytester.path / "test_doc.rst"
    page.write_text(THREE_BLOCK_REST, encoding="utf-8")

    collected = pytester.runpytest(str(page), "--collect-only", "-q")

    collected.stdout.fnmatch_lines(
        [
            "test_doc.rst::test_doc.rst[[]0[]]",
            "test_doc.rst::test_doc.rst[[]1[]]",
            "test_doc.rst::test_doc.rst[[]2[]]",
        ],
        consecutive=True,
    )

    result = pytester.runpytest(str(page), "-rs")

    result.assert_outcomes(passed=1, skipped=2)
    result.stdout.fnmatch_lines(
        [
            "SKIPPED [[]1[]] *: test_doc.rst:6: every example skipped",
            "SKIPPED [[]1[]] *: test_doc.rst:11: every example skipped",
        ],
    )


def test_skipif_block_is_selectable_by_node_id(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The skipped block keeps a node id a reader can run on its own.

    Dropping it left nothing to select; marking it ``SKIP`` leaves the item
    addressable, which is what makes ``-rs`` and IDE test discovery agree.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    page = pytester.path / "test_doc.rst"
    page.write_text(THREE_BLOCK_REST, encoding="utf-8")

    result = pytester.runpytest(f"{page}::test_doc.rst[0]")

    result.assert_outcomes(skipped=1)


GATED_GROUP_REST = textwrap.dedent(
    """
    Example
    =======

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


def test_skipif_leaves_the_rest_of_its_group_running(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Skipping one block of a group is not skipping the group's item.

    The group's item passes on the strength of the blocks that did run, and
    the gated block is an item of its own that reports skipped with a node id
    and a reason. The skipped block would raise if it ran, and the last block
    needs a name the first one bound, which pins both halves of that claim.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    page = pytester.path / "test_doc.rst"
    page.write_text(GATED_GROUP_REST, encoding="utf-8")

    result = pytester.runpytest(str(page), "-rs", "-v")

    result.assert_outcomes(passed=1, skipped=1)
    result.stdout.fnmatch_lines(
        [
            "test_doc.rst::intro PASSED*",
            "test_doc.rst::intro[[]1[]] SKIPPED*",
        ],
        consecutive=True,
    )
    result.stdout.fnmatch_lines(
        ["SKIPPED [[]1[]] *: test_doc.rst:*: every example skipped"],
    )


def test_a_gated_block_of_a_group_is_selectable(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The item a gated block collects as answers to its own node id.

    A reader who sees the skip in ``-rs`` can paste the id back to pytest and
    get the same one line, which is what makes the report actionable.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    page = pytester.path / "test_doc.rst"
    page.write_text(GATED_GROUP_REST, encoding="utf-8")

    result = pytester.runpytest(f"{page}::intro[1]", "-rs")

    result.assert_outcomes(skipped=1)


def test_a_group_skipped_end_to_end_reports_skipped(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A group whose every block is skipped reports as one skipped item.

    The two spellings mix inside a single namespace, and pytest reports the
    item skipped exactly when no example in it is left to run.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    page = pytester.path / "test_doc.rst"
    page.write_text(
        textwrap.dedent(
            """
            Example
            =======

            .. doctest:: solo
                :skipif: True

                >>> 1 / 0

            .. doctest:: solo
                :options: +SKIP

                >>> 1 / 0
            """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest(str(page), "-rs")

    result.assert_outcomes(skipped=1)


def test_skipif_reaches_setup_and_cleanup_under_pytest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A skipped ``testsetup`` or ``testcleanup`` does not run its examples.

    Both directives declare ``skipif``, and both would fail the group's item
    if their examples ran. Each reports as its own skipped item, so a group
    running without the setup it was written with is visible in the report.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    page = pytester.path / "test_doc.rst"
    page.write_text(
        textwrap.dedent(
            """
            Example
            =======

            .. testsetup:: fixture
                :skipif: True

                >>> raise AssertionError("the skipped testsetup ran")

            .. doctest:: fixture

                >>> 2 + 2
                4

            .. testcleanup:: fixture
                :skipif: True

                >>> raise AssertionError("the skipped testcleanup ran")
            """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest(str(page), "-v")

    result.assert_outcomes(passed=1, skipped=2)
    result.stdout.fnmatch_lines(
        [
            "test_doc.rst::fixture[[]0[]] SKIPPED*",
            "test_doc.rst::fixture PASSED*",
            "test_doc.rst::fixture[[]2[]] SKIPPED*",
        ],
        consecutive=True,
    )


def test_collect_only_evaluates_the_skipif_expression(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Listing a page's items runs its ``:skipif:`` expressions.

    The option's contract is a Python expression evaluated while the page is
    read, and ``--collect-only`` reads the page. Marking the block ``SKIP``
    instead of dropping it changes what the reader sees, not when the
    expression is answered — so a page whose expression touches the world
    still touches it during discovery.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest")
    witness = pytester.path / "collect-only-ran.txt"
    # Writes the witness file, then evaluates false, so the block still runs.
    expression = (
        f'__import__("pathlib").Path({str(witness)!r}).write_text("ran") and False'
    )
    page = pytester.path / "test_doc.rst"
    page.write_text(
        textwrap.dedent(
            f"""
            Example
            =======

            .. doctest::
                :skipif: {expression}

                >>> 2 + 2
                4
            """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest(str(page), "--collect-only", "-q")

    result.stdout.fnmatch_lines(["test_doc.rst::test_doc.rst[[]0[]]"])
    assert witness.read_text(encoding="utf-8") == "ran"
