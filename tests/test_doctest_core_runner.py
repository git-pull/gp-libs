"""Tests for fresh materialization and group execution."""

from __future__ import annotations

import doctest
import pathlib
import sys
import traceback

from doctest_core import (
    Counts,
    ExampleRecipe,
    Failed,
    GroupPlan,
    Passed,
    Phase,
    ProjectedBlock,
    RunSettings,
    build_registry,
    materialize,
    parse_document,
    project,
    reset_globs,
    run_group,
)


def test_materializes_fresh_stock_objects_against_one_mapping() -> None:
    """Plans retain recipes while attempts receive ordinary fresh objects."""
    parsed = parse_document(">>> 1 + 1\n2\n", pathlib.Path("guide.rst"))
    block = project(parsed, document_name="guide")[0].blocks[0]
    globs: dict[str, object] = {}

    first = materialize(block, globs)
    second = materialize(block, globs)

    assert type(first) is doctest.DocTest
    assert type(first.examples[0]) is doctest.Example
    assert first is not second
    assert first.examples[0] is not second.examples[0]
    assert first.globs is globs
    assert second.globs is globs
    assert first.examples[0].source == "1 + 1\n"
    assert first.examples[0].want == "2\n"


def test_group_runner_shares_state_and_always_runs_cleanup() -> None:
    """Separate block tests share one mapping owned by their group attempt."""
    source = """
.. testsetup:: example

   value = 40

.. doctest:: example

   >>> value + 2
   42

.. doctest:: example

   >>> value + 3
   99

.. testcleanup:: example

   cleaned = True
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {"residue": "old"}
    identity = id(globs)
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(continue_on_failure=False),
        registry=build_registry(),
    )

    assert id(globs) == identity
    assert "residue" not in globs
    assert globs["cleaned"] is True
    assert isinstance(result.blocks[0], Passed)
    assert isinstance(result.blocks[1], Passed)
    assert isinstance(result.blocks[2], Failed)
    failure = result.blocks[2].failures[0]
    assert failure.test.name == "guide::example[2]"
    assert failure.test.globs is globs
    assert result.primary is None


def test_exec_profile_pairs_testcode_output() -> None:
    """Prompt-free Sphinx code uses its paired output and shared globals."""
    source = """
.. testsetup:: example

   value = 41

.. testcode:: example

   print(value + 1)

.. testoutput:: example

   42
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Passed, Passed]
    test_result = result.blocks[-1]
    assert isinstance(test_result, Passed)
    assert test_result.counts == Counts(failed=0, attempted=1, skipped=0)


def test_reset_globs_reseeds_each_attempt() -> None:
    """A second attempt cannot observe mutations left by its predecessor."""
    parsed = parse_document(">>> token\n'fresh'\n", pathlib.Path("guide.rst"))
    plan = project(parsed, document_name="guide", seed={"token": "fresh"})[0]
    globs: dict[str, object] = {}

    reset_globs(plan, globs)
    globs["token"] = "mutated"
    reset_globs(plan, globs, extraglobs={"fixture": 42})

    assert globs == {"token": "fresh", "fixture": 42, "__name__": "__main__"}


def test_gate_error_is_recorded_and_cleanup_still_runs() -> None:
    """An author-controlled gate cannot escape the group cleanup boundary."""
    source = """
.. doctest:: shared
   :skipif: 1 / 0

   >>> value = 42

.. testcleanup:: shared

   cleaned = True
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert isinstance(result.primary, ZeroDivisionError)
    assert globs["cleaned"] is True
    assert [type(block).__name__ for block in result.blocks] == [
        "Errored",
        "Passed",
    ]


def test_exec_profile_does_not_inherit_core_future_flags() -> None:
    """Exec bodies inherit document state, not this module's future imports."""
    source = """
.. testcode:: shared

   def identity(value: int) -> int:
       return value
   print(identity.__annotations__)

.. testoutput:: shared

   {'value': <class 'int'>, 'return': <class 'int'>}
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block).__name__ for block in result.blocks] == ["Passed"]


def test_exec_profile_restores_stdout_and_records_unexpected_exception() -> None:
    """The extended lane restores process state and emits stock failures."""
    source = """
.. testcode:: shared

   print("before")
   raise ValueError("boom")
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)
    stdout = sys.stdout

    result = run_group(plan, globs)

    assert sys.stdout is stdout
    block = result.blocks[0]
    assert isinstance(block, Failed)
    assert isinstance(block.failures[0], doctest.UnexpectedException)
    assert block.counts == Counts(failed=1, attempted=1, skipped=0)
    rendered = "".join(traceback.format_exception(*block.failures[0].exc_info))
    assert "src/doctest_core/runner.py" not in rendered
    assert "<doctest guide::shared[0][0]>" in rendered


def test_default_exception_policy_retains_system_exit() -> None:
    """The host-neutral default matches CPython's unexpected-exception rule."""
    plan = project(
        parse_document(">>> raise SystemExit(7)\n", pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    block = result.blocks[0]
    assert isinstance(block, Failed)
    assert isinstance(block.failures[0], doctest.UnexpectedException)
    assert result.primary is None


def test_prompt_profile_uses_stock_fail_fast_and_skip_accounting() -> None:
    """Prompt execution retains CPython's option merge and attempt counts."""
    source = """
.. doctest:: shared

   >>> 1 + 1  # doctest: +SKIP
   99
   >>> 2 + 2
   5
   >>> 3 + 3
   6
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(continue_on_failure=False),
    )

    block = result.blocks[0]
    assert isinstance(block, Failed)
    stock_has_skip_count = hasattr(doctest.TestResults(0, 0), "skipped")
    expected_attempts = 2 if stock_has_skip_count else 1
    assert block.counts == Counts(failed=1, attempted=expected_attempts, skipped=1)
    assert len(block.failures) == 1


def test_prompt_skip_count_excludes_unreached_examples() -> None:
    """Old CPython fallback counts only skips reached before fail-fast."""
    source = """
.. doctest:: shared

   >>> 1 + 1
   3
   >>> 2 + 2  # doctest: +SKIP
   4
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(
            optionflags=doctest.FAIL_FAST,
            continue_on_failure=True,
        ),
    )

    block = result.blocks[0]
    assert isinstance(block, Failed)
    assert block.counts == Counts(failed=1, attempted=1, skipped=0)


def test_report_only_first_retains_total_failure_count() -> None:
    """Report suppression does not reduce typed or summary failure totals."""
    source = """
.. doctest:: shared

   >>> 1 + 1
   3
   >>> 2 + 2
   5
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE,
            continue_on_failure=True,
        ),
    )

    block = result.blocks[0]
    assert isinstance(block, Failed)
    assert block.counts == Counts(failed=2, attempted=2, skipped=0)
    assert len(block.failures) == 1


def test_report_only_hidden_fail_fast_bounds_old_skip_fallback() -> None:
    """A quiet stopping failure does not make later skips look examined."""
    source = """
.. doctest:: shared

   >>> 1 + 1
   3
   >>> 2 + 2  # doctest: +FAIL_FAST
   5
   >>> 3 + 3  # doctest: +SKIP
   6
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE,
            continue_on_failure=True,
        ),
    )

    block = result.blocks[0]
    assert isinstance(block, Failed)
    assert block.counts == Counts(failed=2, attempted=2, skipped=0)
    assert len(block.failures) == 1


def test_inline_report_only_preserves_cpython_sequencing() -> None:
    """Prompt reporting retains CPython's previous-example option timing."""
    source = """
.. doctest:: shared

   >>> 1 + 1  # doctest: +REPORT_ONLY_FIRST_FAILURE
   3
   >>> 2 + 2
   5
   >>> 3 + 3
   7
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    block = result.blocks[0]
    assert isinstance(block, Failed)
    assert block.counts == Counts(failed=3, attempted=3, skipped=0)
    assert [failure.example.source for failure in block.failures] == [
        "1 + 1  # doctest: +REPORT_ONLY_FIRST_FAILURE\n",
        "3 + 3\n",
    ]


def test_exec_profile_honors_explicit_fail_fast_option() -> None:
    """The extended lane keeps runner flags distinct from host continuation."""
    source = """
.. testcode:: shared

   print(1)

.. testoutput:: shared

   2

.. testcode:: shared

   print(3)

.. testoutput:: shared

   4
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(
            optionflags=doctest.FAIL_FAST,
            continue_on_failure=True,
        ),
    )

    assert len(result.blocks) == 1
    assert isinstance(result.blocks[0], Failed)


def test_default_run_settings_continue_across_failed_blocks() -> None:
    """The host-neutral default follows doctest and Sphinx continuation."""
    source = """
.. doctest:: shared

   >>> 1 + 1
   3

.. doctest:: shared

   >>> 2 + 2
   5
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Failed, Failed]


def test_host_stop_policy_cannot_be_disabled_inline() -> None:
    """An example cannot override the host's debugger-style stop policy."""
    source = """
.. doctest:: shared

   >>> state = []
   >>> 1 + 1  # doctest: -FAIL_FAST
   3
   >>> state.append("ran")
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(continue_on_failure=False),
    )

    assert isinstance(result.blocks[0], Failed)
    assert result.blocks[0].counts == Counts(failed=1, attempted=2, skipped=0)
    assert globs["state"] == []


def test_cleanup_abort_is_not_demoted_after_test_failure() -> None:
    """A process abort from cleanup remains stronger than block failures."""
    source = """
.. testcode:: shared

   print(1)

.. testoutput:: shared

   2

.. testcleanup:: shared

   raise KeyboardInterrupt()
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert isinstance(result.blocks[0], Failed)
    assert isinstance(result.primary, KeyboardInterrupt)


def test_exec_profile_accepts_expected_exception() -> None:
    """A Sphinx testoutput traceback supplies the stock expected exception."""
    source = """
.. testcode:: shared

   raise ValueError("boom")

.. testoutput:: shared

   Traceback (most recent call last):
   ...
   ValueError: boom
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Passed]


def test_exec_profile_ignores_stdout_before_expected_exception() -> None:
    """Expected exceptions compare the exception tail, as CPython does."""
    source = """
.. testcode:: shared

   print("before")
   raise ValueError("boom")

.. testoutput:: shared

   Traceback (most recent call last):
   ...
   ValueError: boom
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Passed]


def test_exec_profile_honors_ignore_exception_detail() -> None:
    """Expected exceptions retain CPython's detail-insensitive fallback."""
    source = """
.. testcode:: shared

   raise ValueError("actual detail")

.. testoutput:: shared
   :options: +IGNORE_EXCEPTION_DETAIL

   Traceback (most recent call last):
   ...
   ValueError: expected detail
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Passed]


def test_expected_exception_mismatch_hides_runtime_frame() -> None:
    """Failure traceback ownership starts at the author's compiled block."""
    source = """
.. testcode:: shared

   raise ValueError("actual")

.. testoutput:: shared

   Traceback (most recent call last):
   ...
   TypeError: expected
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    block = result.blocks[0]
    assert isinstance(block, Failed)
    failure = block.failures[0]
    assert isinstance(failure, doctest.DocTestFailure)
    assert "src/doctest_core/runner.py" not in failure.got
    assert "<doctest guide::shared[0][0]>" in failure.got


def test_exec_profile_normalizes_missing_stdout_newline() -> None:
    """Extended output keeps doctest's unrepresentable-newline convention."""
    source = """
.. testcode:: shared

   import sys
   sys.stdout.write("answer")

.. testoutput:: shared

   answer
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Passed]


def test_exec_profile_normalizes_syntax_error_details() -> None:
    """Syntax errors compare from the exception line across Python versions."""
    source = """
.. testcode:: shared

   compile("if:", "bad.py", "exec")

.. testoutput:: shared

   Traceback (most recent call last):
   ...
   SyntaxError: invalid syntax
"""
    plan = project(
        parse_document(source, pathlib.Path("guide.rst")),
        document_name="guide",
    )[0]
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(plan, globs)

    assert [type(block) for block in result.blocks] == [Passed]


def test_exec_profile_honors_inline_fail_fast() -> None:
    """The current example's effective flags control extended execution."""
    block = ProjectedBlock(
        phase=Phase.TEST,
        name="guide::shared[0]",
        block_ordinal=0,
        examples=(
            ExampleRecipe(
                source='print("first")\n',
                want="wrong\n",
                exc_msg=None,
                lineno=0,
                indent=0,
                options={doctest.FAIL_FAST: True},
            ),
            ExampleRecipe(
                source='print("second")\n',
                want="wrong\n",
                exc_msg=None,
                lineno=1,
                indent=0,
                options={},
            ),
        ),
        docstring="",
        filename="guide.rst",
        lineno=0,
        options={},
        profile_name="exec",
        skipif=None,
        pyversion=None,
        expected=None,
    )
    plan = GroupPlan("shared", (block,), {})
    globs: dict[str, object] = {}
    reset_globs(plan, globs)

    result = run_group(
        plan,
        globs,
        settings=RunSettings(continue_on_failure=True),
    )

    assert isinstance(result.blocks[0], Failed)
    assert result.blocks[0].counts == Counts(failed=1, attempted=1, skipped=0)
