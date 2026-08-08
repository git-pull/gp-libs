"""Fresh materialization and host-neutral group execution."""

from __future__ import annotations
import __future__

import contextlib
import doctest
import io
import sys
import traceback
import types
import typing as t

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .contracts import (
    ExceptionPolicy,
    ExecutionRuntime,
    RuntimeOutcome,
    RuntimeSettings,
)
from .model import (
    BlockResult,
    Counts,
    Errored,
    Failed,
    Failure,
    GroupPlan,
    GroupResult,
    Passed,
    Phase,
    ProjectedBlock,
    Skipped,
    SkipReason,
)
from .settings import RunSettings

if t.TYPE_CHECKING:
    from doctest import _Out

    from .registry import RegistrySnapshot


class DefaultExceptionPolicy:
    """Preserve the standard-library doctest exception boundary."""

    def should_propagate(self, error: BaseException) -> bool:
        """Return whether ``error`` must escape doctest handling.

        >>> DefaultExceptionPolicy().should_propagate(KeyboardInterrupt())
        True
        >>> DefaultExceptionPolicy().should_propagate(ValueError())
        False
        """
        return isinstance(error, KeyboardInterrupt)

    def is_abort(self, error: BaseException) -> bool:
        """Return whether ``error`` must outrank block and cleanup results.

        >>> DefaultExceptionPolicy().is_abort(SystemExit())
        False
        >>> DefaultExceptionPolicy().is_abort(ValueError())
        False
        """
        return isinstance(error, KeyboardInterrupt)


def _results(failed: int, attempted: int, skipped: int) -> doctest.TestResults:
    """Construct ``TestResults`` across CPython's supported shapes."""
    try:
        constructor = t.cast(t.Any, doctest.TestResults)
        return t.cast(
            doctest.TestResults,
            constructor(failed, attempted, skipped=skipped),
        )
    except TypeError:
        return doctest.TestResults(failed, attempted)


def _effective_flags(defaults: int, options: t.Mapping[int, bool]) -> int:
    """Apply per-example boolean overrides to an option bitmask."""
    flags = defaults
    for flag, enabled in options.items():
        if enabled:
            flags |= flag
        else:
            flags &= ~flag
    return flags


def _compile_flags(globs: t.Mapping[str, t.Any]) -> int:
    """Return future-feature compiler flags already active in ``globs``.

    >>> _compile_flags({})
    0
    """
    flags = 0
    for name in __future__.all_feature_names:
        feature: t.Any = getattr(__future__, name)
        compiler_flag: int = feature.compiler_flag
        if globs.get(name) is feature:
            flags |= compiler_flag
    return flags


def _captured_output(stream: io.StringIO) -> str:
    r"""Return captured stdout with doctest's implied trailing newline.

    >>> stream = io.StringIO("partial")
    >>> _captured_output(stream)
    'partial\n'
    """
    output = stream.getvalue()
    if output and not output.endswith("\n"):
        return f"{output}\n"
    return output


class _CollectingRunner(doctest.DocTestRunner):
    """Stock prompt runner with pytest-neutral failure collection."""

    def __init__(self, settings: RuntimeSettings) -> None:
        super().__init__(
            checker=settings.checker,
            optionflags=settings.optionflags,
        )
        self.original_optionflags = settings.optionflags
        self.continue_on_failure = settings.continue_on_failure
        self.exception_policy = settings.exception_policy
        self.recorded_failures: list[Failure] = []

    def report_failure(
        self,
        out: _Out,
        test: doctest.DocTest,
        example: doctest.Example,
        got: str,
    ) -> None:
        """Retain a comparison failure for the embedding host."""
        del out
        self.recorded_failures.append(doctest.DocTestFailure(test, example, got))
        if not self.continue_on_failure:
            self.optionflags |= doctest.FAIL_FAST

    def report_unexpected_exception(
        self,
        out: _Out,
        test: doctest.DocTest,
        example: doctest.Example,
        exc_info: tuple[
            type[BaseException],
            BaseException,
            types.TracebackType,
        ],
    ) -> None:
        """Retain Python failures while propagating host-owned exceptions."""
        del out
        if self.exception_policy.should_propagate(exc_info[1]):
            raise exc_info[1]
        self.recorded_failures.append(
            doctest.UnexpectedException(test, example, exc_info),
        )
        if not self.continue_on_failure:
            self.optionflags |= doctest.FAIL_FAST


class PromptRuntime:
    """Execute prompt-form examples on CPython's untouched example loop."""

    def __init__(self, settings: RuntimeSettings) -> None:
        self.runner = _CollectingRunner(settings)

    def run(self, test: doctest.DocTest) -> RuntimeOutcome:
        """Run a stock doctest without clearing its shared globals."""
        self.runner.recorded_failures.clear()
        results = self.runner.run(
            test,
            out=lambda _: None,
            clear_globs=False,
        )
        failures = tuple(self.runner.recorded_failures)
        skipped = getattr(results, "skipped", None)
        if skipped is None:
            skipped = _prompt_skipped(test, failures, self.runner)
        return RuntimeOutcome(results, failures, skipped)


def _prompt_skipped(
    test: doctest.DocTest,
    failures: tuple[Failure, ...],
    runner: _CollectingRunner,
) -> int:
    """Reconstruct reached skips on CPython versions that do not report them."""
    stop_index: int | None = None
    if failures:
        first_failure = test.examples.index(failures[0].example)
        if not runner.continue_on_failure:
            stop_index = first_failure
        else:
            for index in range(first_failure, len(test.examples)):
                example = test.examples[index]
                flags = _effective_flags(
                    runner.original_optionflags,
                    example.options,
                )
                if flags & doctest.SKIP:
                    continue
                if flags & doctest.FAIL_FAST:
                    stop_index = index
                    break
    reached = test.examples if stop_index is None else test.examples[: stop_index + 1]
    return sum(
        bool(
            _effective_flags(runner.original_optionflags, example.options)
            & doctest.SKIP
        )
        for example in reached
    )


class ExecRuntime:
    """Execute prompt-free Sphinx blocks with doctest comparison semantics."""

    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings

    def run(self, test: doctest.DocTest) -> RuntimeOutcome:
        """Run examples in ``exec`` mode against the test's live mapping."""
        failures: list[Failure] = []
        attempted = 0
        skipped = 0
        for index, example in enumerate(test.examples):
            attempted += 1
            flags = _effective_flags(self.settings.optionflags, example.options)
            if flags & doctest.SKIP:
                skipped += 1
                continue
            got_stream = io.StringIO()
            exc_info: (
                tuple[
                    type[BaseException],
                    BaseException,
                    types.TracebackType | None,
                ]
                | None
            ) = None
            try:
                code = compile(
                    example.source,
                    f"<doctest {test.name}[{index}]>",
                    "exec",
                    _compile_flags(test.globs),
                    dont_inherit=True,
                )
                with contextlib.redirect_stdout(got_stream):
                    # Doctests execute author-provided Python by definition.
                    exec(code, test.globs)  # noqa: S102
            except BaseException as error:
                if self.settings.exception_policy.should_propagate(error):
                    raise
                traceback_head = error.__traceback__
                exc_info = (
                    type(error),
                    error,
                    None if traceback_head is None else traceback_head.tb_next,
                )

            got = _captured_output(got_stream)
            failure = self._compare(test, example, got, exc_info, flags)
            if failure is not None:
                failures.append(failure)
                if not self.settings.continue_on_failure or flags & doctest.FAIL_FAST:
                    break
        return RuntimeOutcome(
            _results(len(failures), attempted, skipped),
            tuple(failures),
            skipped,
        )

    def _compare(
        self,
        test: doctest.DocTest,
        example: doctest.Example,
        got: str,
        exc_info: tuple[
            type[BaseException],
            BaseException,
            types.TracebackType | None,
        ]
        | None,
        flags: int,
    ) -> Failure | None:
        """Return a stock failure object when one example does not match."""
        if exc_info is not None:
            if example.exc_msg is None:
                return doctest.UnexpectedException(
                    test,
                    example,
                    t.cast(t.Any, exc_info),
                )
            formatted = traceback.format_exception_only(exc_info[0], exc_info[1])
            if issubclass(exc_info[0], SyntaxError):
                prefixes = (
                    f"{exc_info[0].__qualname__}:",
                    f"{exc_info[0].__module__}.{exc_info[0].__qualname__}:",
                )
                message_index = next(
                    index
                    for index, line in enumerate(formatted)
                    if line.startswith(prefixes)
                )
                formatted = formatted[message_index:]
            exc_msg = "".join(formatted)
            if self.settings.checker.check_output(example.exc_msg, exc_msg, flags):
                return None
            if flags & doctest.IGNORE_EXCEPTION_DETAIL:
                expected = _strip_exception_details(example.exc_msg)
                actual = _strip_exception_details(exc_msg)
                if self.settings.checker.check_output(expected, actual, flags):
                    return None
            traceback_text = "".join(traceback.format_exception(*exc_info))
            return doctest.DocTestFailure(test, example, got + traceback_text)
        if example.exc_msg is not None:
            return doctest.DocTestFailure(test, example, got)
        if self.settings.checker.check_output(example.want, got, flags):
            return None
        return doctest.DocTestFailure(test, example, got)


def _strip_exception_details(message: str) -> str:
    r"""Retain only the exception name for detail-insensitive comparison.

    >>> _strip_exception_details("package.Error: detail\n")
    'Error'
    """
    line = message.split("\n", 1)[0]
    name = line.split(":", 1)[0]
    return name.rsplit(".", 1)[-1]


class PromptExecutionProfile:
    """Factory for the vanilla prompt runtime."""

    def open(
        self,
        settings: RuntimeSettings,
    ) -> contextlib.AbstractContextManager[ExecutionRuntime]:
        """Return an attempt-local prompt runtime."""
        return contextlib.nullcontext(PromptRuntime(settings))


class ExecExecutionProfile:
    """Factory for prompt-free ``testcode`` and phase blocks."""

    def open(
        self,
        settings: RuntimeSettings,
    ) -> contextlib.AbstractContextManager[ExecutionRuntime]:
        """Return an attempt-local exec runtime."""
        return contextlib.nullcontext(ExecRuntime(settings))


def _expected_enabled(
    block: ProjectedBlock,
    globs: dict[str, t.Any],
) -> bool:
    """Evaluate the paired output's gates against the live group mapping."""
    expected = block.expected
    if expected is None:
        return False
    if expected.skipif is not None and bool(eval(expected.skipif, globs)):
        return False
    return expected.pyversion is None or _version_allowed(expected.pyversion)


def _exception_message(want: str) -> str | None:
    r"""Extract doctest's expected exception tail from paired output.

    >>> _exception_message(
    ...     'Traceback (most recent call last):\n...\nValueError: bad\n'
    ... )
    'ValueError: bad\n'
    >>> _exception_message('ordinary output\n') is None
    True
    """
    match = doctest.DocTestParser._EXCEPTION_RE.match(want)  # type: ignore[attr-defined]
    return match.group("msg") if match is not None else None


def materialize(
    block: ProjectedBlock,
    globs: dict[str, t.Any],
    *,
    expected_enabled: bool = True,
) -> doctest.DocTest:
    r"""Build fresh stock ``Example`` and ``DocTest`` objects for an attempt.

    >>> import doctest
    >>> type(doctest.Example("pass\n", "")) is doctest.Example
    True
    """
    examples: list[doctest.Example] = []
    for index, recipe in enumerate(block.examples):
        options = dict(block.options)
        want = recipe.want
        exc_msg = recipe.exc_msg
        if block.expected is not None:
            if expected_enabled:
                options.update(block.expected.options)
                options[doctest.DONT_ACCEPT_BLANKLINE] = True
                want = block.expected.text
                exc_msg = _exception_message(want)
            else:
                want = ""
                exc_msg = None
        options.update(recipe.options)
        examples.append(
            doctest.Example(
                source=recipe.source,
                want=want,
                exc_msg=exc_msg,
                lineno=recipe.lineno,
                indent=recipe.indent,
                options=options,
            ),
        )
        if block.expected is not None and index == 0:
            break
    test = doctest.DocTest(
        examples,
        globs,
        block.name,
        block.filename,
        block.lineno,
        block.docstring,
    )
    test.globs = globs
    return test


def reset_globs(
    plan: GroupPlan,
    globs: dict[str, t.Any],
    *,
    extraglobs: t.Mapping[str, t.Any] | None = None,
) -> None:
    """Clear and reseed one canonical group mapping in place.

    >>> mapping = {"old": True}
    >>> reset_globs(GroupPlan("default", (), {"seed": 1}), mapping)
    >>> mapping
    {'seed': 1, '__name__': '__main__'}
    """
    globs.clear()
    globs.update(plan.seed)
    if extraglobs is not None:
        globs.update(extraglobs)
    globs.setdefault("__name__", "__main__")


def _version_allowed(specifier: str) -> bool:
    """Return whether the current interpreter satisfies a PEP 440 specifier."""
    version = Version(".".join(str(part) for part in sys.version_info[:3]))
    return version in SpecifierSet(specifier)


def _block_gate(
    block: ProjectedBlock,
    globs: dict[str, t.Any],
) -> SkipReason | None:
    """Evaluate one block gate at the execution boundary."""
    if block.skipif is not None and bool(eval(block.skipif, globs)):
        return SkipReason("skipif", block.skipif)
    if block.pyversion is not None and not _version_allowed(block.pyversion):
        return SkipReason("pyversion", block.pyversion)
    return None


def _run_block(
    block: ProjectedBlock,
    globs: dict[str, t.Any],
    runtime: ExecutionRuntime,
    checker: doctest.OutputChecker,
    settings: RunSettings,
) -> BlockResult:
    """Gate, materialize, and run one projected block."""
    try:
        gate = _block_gate(block, globs)
        if gate is not None:
            return Skipped(block, Counts(0, 0, 0), gate)
        expected_enabled = _expected_enabled(block, globs)
        test = materialize(block, globs, expected_enabled=expected_enabled)
        outcome = runtime.run(test)
    # The exception policy decides which host and process outcomes propagate.
    except BaseException as error:  # noqa: BLE001
        return Errored(block, error)
    counts = Counts(
        outcome.results.failed,
        outcome.results.attempted,
        outcome.skipped,
    )
    if outcome.failures:
        return Failed(block, counts, outcome.failures, checker)
    if test.examples and outcome.skipped == len(test.examples):
        return Skipped(
            block,
            counts,
            SkipReason("inline-flag", "SKIP"),
        )
    return Passed(block, counts)


def run_group(
    plan: GroupPlan,
    globs: dict[str, t.Any],
    *,
    settings: RunSettings | None = None,
    registry: RegistrySnapshot | None = None,
    exception_policy: ExceptionPolicy | None = None,
) -> GroupResult:
    """Run one group attempt with setup/test/cleanup phase semantics."""
    if registry is None:
        from .registry import build_registry

        registry = build_registry()
    settings = settings or RunSettings()
    exception_policy = exception_policy or DefaultExceptionPolicy()
    checker_registration = registry.output_checkers[settings.checker_name]
    results: list[BlockResult] = []
    primary: BaseException | None = None
    secondary: list[BaseException] = []
    body_failed = False
    stop_after_failure = not settings.continue_on_failure or bool(
        settings.optionflags & doctest.FAIL_FAST
    )

    with contextlib.ExitStack() as stack:
        runtimes: dict[str, ExecutionRuntime] = {}
        checkers: dict[str, doctest.OutputChecker] = {}
        for profile_name in dict.fromkeys(block.profile_name for block in plan.blocks):
            profile = registry.execution_profiles[profile_name].value
            checker = checker_registration.value()
            runtime_settings = RuntimeSettings(
                optionflags=settings.optionflags,
                continue_on_failure=settings.continue_on_failure,
                checker=checker,
                exception_policy=exception_policy,
            )
            checkers[profile_name] = checker
            runtimes[profile_name] = stack.enter_context(profile.open(runtime_settings))

        setup_failed = False
        for phase in (Phase.SETUP, Phase.TEST):
            if phase is Phase.TEST and setup_failed:
                break
            for block in (item for item in plan.blocks if item.phase is phase):
                result = _run_block(
                    block,
                    globs,
                    runtimes[block.profile_name],
                    checkers[block.profile_name],
                    settings,
                )
                results.append(result)
                if isinstance(result, Errored):
                    primary = result.error
                    body_failed = True
                    setup_failed = phase is Phase.SETUP
                    break
                if isinstance(result, Failed):
                    body_failed = True
                    setup_failed = phase is Phase.SETUP
                    if setup_failed or stop_after_failure:
                        break
            if primary is not None or setup_failed:
                break

        for block in (item for item in plan.blocks if item.phase is Phase.CLEANUP):
            result = _run_block(
                block,
                globs,
                runtimes[block.profile_name],
                checkers[block.profile_name],
                settings,
            )
            results.append(result)
            if isinstance(result, Errored):
                if exception_policy.is_abort(result.error):
                    if primary is None or not exception_policy.is_abort(primary):
                        if primary is not None:
                            secondary.append(primary)
                        primary = result.error
                    else:
                        secondary.append(result.error)
                elif primary is None and not body_failed:
                    primary = result.error
                else:
                    secondary.append(result.error)

    return GroupResult(plan.group, tuple(results), primary, tuple(secondary))
