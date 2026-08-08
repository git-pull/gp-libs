"""Host-boundary acceptance tests for grouped doctest execution."""

from __future__ import annotations

import textwrap

import _pytest.pytester
import pytest


def test_rerun_reseeds_group_globs(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A rerun cannot pass by observing mutations from its first attempt."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest:: shared

               >>> attempt = globals().get("attempt", 0) + 1
               >>> attempt
               2
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "--reruns", "1", "-q")

    result.assert_outcomes(failed=1)
    assert result.parseoutcomes()["rerun"] == 1


@pytest.mark.parametrize("distribution", ["load", "worksteal"])
def test_xdist_runs_stateful_groups_without_affinity(
    pytester: _pytest.pytester.Pytester,
    distribution: str,
) -> None:
    """Each xdist scheduler may move groups without splitting group state."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            @pytest.fixture(autouse=True)
            def inject_worker(doctest_namespace, worker_id):
                doctest_namespace["worker_id"] = worker_id
            """,
        ),
    )
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest:: first

               >>> state = [worker_id, "first"]

            .. doctest:: first

               >>> state[0].startswith("gw")
               True
               >>> state[1]
               'first'

            .. doctest:: second

               >>> state = [worker_id, "second"]

            .. doctest:: second

               >>> state[0].startswith("gw")
               True
               >>> state[1]
               'second'
            """,
        ),
    )

    result = pytester.runpytest(
        "guide.rst",
        "-n",
        "2",
        "--dist",
        distribution,
        "-q",
    )

    result.assert_outcomes(passed=2)
    assert result.ret is pytest.ExitCode.OK


def test_pytest_asyncio_fixture_composes_with_document_item(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """An async autouse fixture can populate the doctest namespace."""
    pytest.importorskip("pytest_asyncio", minversion="1.0")
    pytester.plugins = ["pytest_doctest_docutils", "pytest_asyncio.plugin"]
    pytester.makeini("[pytest]\nasyncio_mode = auto\n")
    pytester.makeconftest(
        textwrap.dedent(
            """
            import asyncio

            import pytest_asyncio

            @pytest_asyncio.fixture(autouse=True)
            async def inject_value(doctest_namespace):
                await asyncio.sleep(0)
                doctest_namespace["value"] = 42
            """,
        ),
    )
    pytester.makefile(
        ".rst",
        guide=textwrap.dedent(
            """
            .. doctest::

               >>> value
               42
            """,
        ),
    )

    result = pytester.runpytest("guide.rst", "-q")

    result.assert_outcomes(passed=1)
