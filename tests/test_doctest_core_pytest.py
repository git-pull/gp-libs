"""End-to-end tests for the typed core's pytest host adapter."""

from __future__ import annotations

import textwrap

import _pytest.pytester
import pytest


def test_pytest_composes_with_builtin_and_collects_one_group(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The adapter keeps pytest doctest active and owns one grouped item."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            def pytest_sessionstart(session):
                assert session.config.pluginmanager.has_plugin("doctest")

            @pytest.fixture(autouse=True)
            def inject(doctest_namespace):
                doctest_namespace["fixture_value"] = 40
            """,
        ),
    )
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest:: shared

               >>> value = fixture_value

            .. doctest:: shared

               >>> value + 2
               42
            """,
        ),
    )
    pytester.makepyfile(
        test_module=textwrap.dedent(
            '''
            def answer():
                """Return the answer.

                >>> answer()
                42
                """
                return 42
            ''',
        ),
    )

    result = pytester.runpytest(
        "guide.rst",
        "test_module.py",
        "--doctest-docutils-modules",
        "-q",
    )

    result.assert_outcomes(passed=2)


def test_pytest_outcome_escapes_and_cleanup_runs(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A host skip remains a skip and cannot bypass group cleanup."""
    pytester.plugins = ["pytest_doctest_docutils"]
    marker = pytester.path / "cleaned"
    pytester.makeconftest(
        textwrap.dedent(
            f"""
            import pathlib
            import pytest

            @pytest.fixture(autouse=True)
            def inject(doctest_namespace):
                doctest_namespace.update(
                    pytest=pytest,
                    marker=pathlib.Path({str(marker)!r}),
                )
            """,
        ),
    )
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest:: shared

               >>> pytest.skip("not available")

            .. testcleanup:: shared

               marker.write_text("yes")
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "-q", "-rs")

    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*SKIPPED*not available*"])
    assert marker.read_text(encoding="utf-8") == "yes"


def test_cleanup_outcome_is_a_failure(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A cleanup skip cannot relabel a completed test as skipped."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            @pytest.fixture(autouse=True)
            def inject(doctest_namespace):
                doctest_namespace["pytest"] = pytest
            """,
        ),
    )
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest:: shared

               >>> 6 * 7
               42

            .. testcleanup:: shared

               pytest.skip("cleanup refused")
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "-q")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*cleanup*cleanup refused*"])


def test_cleanup_outcome_is_reported_beside_primary_failure(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A secondary cleanup outcome remains visible beside the primary failure."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            @pytest.fixture(autouse=True)
            def inject(doctest_namespace):
                doctest_namespace["pytest"] = pytest
            """,
        ),
    )
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest:: shared

               >>> 1 + 1
               3

            .. testcleanup:: shared

               pytest.skip("cleanup refused after failure")
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "-q")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        ["*doctest cleanup*", "*cleanup refused after failure*"],
    )


def test_pytest_direct_path_has_no_builtin_duplicate(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The collector wrapper removes pytest's textfile collector before parse."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".rst",
        guide=">>> 6 * 7\n42\n",
    )

    result = pytester.runpytest("guide.rst", "--collect-only", "-q")

    result.assert_outcomes(errors=0)
    result.stdout.fnmatch_lines(["*1 test collected*"])


def test_anonymous_item_does_not_collide_with_named_group(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A bare block and a same-named author group get separate items and state."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            >>> marker = "anonymous"

            .. doctest:: block-0

               >>> "marker" in globals()
               False
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "-q")

    result.assert_outcomes(passed=2)


@pytest.mark.parametrize("body", ["", "value = 42"])
def test_pytest_does_not_collect_prompt_free_doctest(
    pytester: _pytest.pytester.Pytester,
    body: str,
) -> None:
    """An empty stock DocTest does not become a passing carrier item."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".rst", guide=f".. doctest::\n\n   {body}\n")

    result = pytester.runpytest("guide.rst", "--collect-only", "-q")

    result.assert_outcomes(errors=0)
    result.stdout.fnmatch_lines(["*no tests collected*"])


def test_custom_doctest_glob_remains_owned_by_pytest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Unsupported parser suffixes remain the built-in plugin's concern."""
    pytester.plugins = ["pytest_doctest_docutils"]
    path = pytester.path / "guide.foo"
    path.write_text(">>> 6 * 7\n42\n", encoding="utf-8")

    result = pytester.runpytest(str(path), "--doctest-glob=*.foo", "-q")

    result.assert_outcomes(passed=1)


def test_pytest_preserves_per_block_failure_locations(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """One group item retains each failed block's source line."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".rst",
        guide=""".. doctest:: shared

   >>> 1 + 1
   3

.. doctest:: shared

   >>> 2 + 2
   5
""",
    )

    result = pytester.runpytest(
        "guide.rst",
        "--doctest-continue-on-failure",
        "-q",
    )

    result.assert_outcomes(failed=1)
    output = result.stdout.str()
    assert "guide.rst:3" in output
    assert "guide.rst:8" in output


def test_contributed_checker_compares_and_explains(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The checker that rejects output also renders the resulting failure."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makeconftest(
        textwrap.dedent(
            """
            import doctest

            from doctest_core import Provider

            class Checker(doctest.OutputChecker):
                def __init__(self):
                    self.compared = False

                def check_output(self, want, got, optionflags):
                    self.compared = True
                    return False

                def output_difference(self, example, got, optionflags):
                    assert self.compared
                    return "CUSTOM CHECKER DIFFERENCE"

            class Contributor:
                provider = Provider("pytest", "probe")

                def contribute(self, registrar):
                    registrar.add_output_checker(
                        "stdlib", Checker, replace=True
                    )

            def pytest_doctest_core_contributors():
                return Contributor()
            """,
        ),
    )
    pytester.makefile(".rst", guide=">>> 6 * 7\n42\n")

    result = pytester.runpytest("guide.rst", "-q")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*CUSTOM CHECKER DIFFERENCE*"])


def test_late_nested_contributor_is_rejected(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A nested conftest cannot silently miss the frozen registry."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makeini("[pytest]\ntestpaths = nested\n")
    nested = pytester.path / "nested"
    nested.mkdir()
    (nested / "conftest.py").write_text(
        textwrap.dedent(
            """
            def pytest_doctest_core_contributors():
                return None
            """,
        ),
        encoding="utf-8",
    )
    (nested / "guide.rst").write_text(">>> 6 * 7\n42\n", encoding="utf-8")

    result = pytester.runpytest(".", "-q")

    assert result.ret is pytest.ExitCode.INTERRUPTED
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*nested/conftest.py*doctest-core contributor*phase closed*"],
    )


def test_document_collection_requires_builtin_doctest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Disabling the composed host fails only an affected documentation path."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".rst", guide=">>> 6 * 7\n42\n")

    result = pytester.runpytest("guide.rst", "-p", "no:doctest", "-q")

    assert result.ret is pytest.ExitCode.INTERRUPTED
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*guide.rst*requires pytest's built-in doctest plugin*"],
    )


def test_discovered_document_requires_builtin_doctest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Directory discovery reaches the same actionable disabled-host error."""
    pytester.plugins = ["pytest_doctest_docutils"]
    docs = pytester.path / "docs"
    docs.mkdir()
    (docs / "guide.rst").write_text(">>> 6 * 7\n42\n", encoding="utf-8")

    result = pytester.runpytest("docs", "-p", "no:doctest", "-q")

    assert result.ret is pytest.ExitCode.INTERRUPTED
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*guide.rst*requires pytest's built-in doctest plugin*"],
    )


def test_cleanup_exit_outranks_doctest_failure(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A cleanup session exit cannot be reduced to a secondary report."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. testcode:: shared

               print(1)

            .. testoutput:: shared

               2

            .. testcleanup:: shared

               import pytest
               pytest.exit("cleanup requested")
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "-q")

    assert result.ret is pytest.ExitCode.INTERRUPTED
    result.stdout.fnmatch_lines(["*Exit: cleanup requested*"])
