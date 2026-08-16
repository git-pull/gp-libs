"""Host-neutral values carried through the doctest pipeline."""

from __future__ import annotations

import doctest
import enum
import pathlib
import typing as t


class Phase(enum.IntEnum):
    """Execution phase for a projected block.

    Setup and cleanup surround test blocks while retaining source order within
    each phase.

    >>> Phase.SETUP < Phase.TEST < Phase.CLEANUP
    True
    """

    SETUP = 0
    TEST = 1
    CLEANUP = 2


class Diagnostic(t.NamedTuple):
    """A parser diagnostic that can cross host boundaries.

    Attributes
    ----------
    level : {"info", "warning", "error"}
        Normalized severity.
    code : str or None
        Stable classifier when the parser provides one.
    message : str
        Human-readable explanation.
    path : pathlib.Path
        Source containing the diagnostic.
    line : int or None
        One-based source line when available.
    """

    level: t.Literal["info", "warning", "error"]
    code: str | None
    message: str
    path: pathlib.Path
    line: int | None


class ParsedBlock(t.NamedTuple):
    """An inert runnable block extracted from markup.

    Attributes
    ----------
    kind : str
        Registered block-kind name.
    source : str
        Dedented author text.
    path : pathlib.Path
        File containing the block.
    line : int or None
        One-based source line when available.
    document_order : int
        Position in the shared block-and-output stream.
    block_ordinal : int
        Stable position among runnable blocks.
    groups : tuple of str
        Author-declared Sphinx group names.
    options : mapping of int to bool
        Doctest option overrides.
    skipif : str or None
        Unevaluated skip expression.
    pyversion : str or None
        Unevaluated PEP 440 version specifier.
    hidden : bool
        Whether the markup hides the block from rendered output.
    """

    kind: str
    source: str
    path: pathlib.Path
    line: int | None
    document_order: int
    block_ordinal: int
    groups: tuple[str, ...]
    options: t.Mapping[int, bool]
    skipif: str | None
    pyversion: str | None
    hidden: bool


class ParsedOutput(t.NamedTuple):
    """An inert expected-output body.

    Attributes
    ----------
    kind : str
        Output-kind name referenced by a registered block kind.
    text : str
        Expected output text.
    path : pathlib.Path
        File containing the output.
    line : int or None
        One-based source line when available.
    document_order : int
        Position in the shared block-and-output stream.
    groups : tuple of str
        Author-declared Sphinx group names.
    options : mapping of int to bool
        Doctest option overrides.
    skipif : str or None
        Unevaluated skip expression.
    pyversion : str or None
        Unevaluated PEP 440 version specifier.
    """

    kind: str
    text: str
    path: pathlib.Path
    line: int | None
    document_order: int
    groups: tuple[str, ...]
    options: t.Mapping[int, bool]
    skipif: str | None
    pyversion: str | None


class ParseResult(t.NamedTuple):
    """Complete typed output of parsing one document.

    Attributes
    ----------
    blocks : tuple of ParsedBlock
        Runnable blocks in source order.
    outputs : tuple of ParsedOutput
        Expected-output records in source order.
    diagnostics : tuple of Diagnostic
        Parser diagnostics retained as data.
    """

    blocks: tuple[ParsedBlock, ...]
    outputs: tuple[ParsedOutput, ...]
    diagnostics: tuple[Diagnostic, ...]


class BlockKind(t.NamedTuple):
    """Projection policy registered for one markup block kind.

    Attributes
    ----------
    phase : Phase
        Phase in which the block executes.
    profile_name : str
        Registered execution-profile name.
    pairs_with : str or None
        Expected-output kind paired with the block, if any.
    """

    phase: Phase
    profile_name: str
    pairs_with: str | None


class ExpectedOutput(t.NamedTuple):
    """Expected output paired with an executable block.

    Attributes
    ----------
    text : str
        Expected output text.
    options : mapping of int to bool
        Output-specific doctest option overrides.
    skipif : str or None
        Unevaluated skip expression.
    pyversion : str or None
        Unevaluated PEP 440 version specifier.
    """

    text: str
    options: t.Mapping[int, bool]
    skipif: str | None
    pyversion: str | None


class ExampleRecipe(t.NamedTuple):
    """Fields needed to rebuild one stock :class:`doctest.Example`.

    Attributes
    ----------
    source : str
        Python source ending in a newline.
    want : str
        Expected output ending in a newline when non-empty.
    exc_msg : str or None
        Expected exception detail.
    lineno : int
        Zero-based line relative to the block.
    indent : int
        Prompt indentation.
    options : mapping of int to bool
        Inline doctest option overrides.
    """

    source: str
    want: str
    exc_msg: str | None
    lineno: int
    indent: int
    options: t.Mapping[int, bool]


class ProjectedBlock(t.NamedTuple):
    """Immutable recipe for one runnable source block.

    Attributes
    ----------
    phase : Phase
        Execution phase.
    name : str
        Unique, machine-independent doctest name.
    block_ordinal : int
        Stable position among runnable source blocks.
    examples : tuple of ExampleRecipe
        Recipes materialized into stock examples per attempt.
    docstring : str
        Source used by failure renderers.
    filename : str
        Source filename shown by doctest and host adapters.
    lineno : int or None
        One-based block line when known.
    options : mapping of int to bool
        Block-level doctest option overrides.
    profile_name : str
        Registered execution-profile name.
    skipif : str or None
        Unevaluated skip expression.
    pyversion : str or None
        Unevaluated PEP 440 version specifier.
    expected : ExpectedOutput or None
        Paired expected output for an executable-code block.
    """

    phase: Phase
    name: str
    block_ordinal: int
    examples: tuple[ExampleRecipe, ...]
    docstring: str
    filename: str
    lineno: int | None
    options: t.Mapping[int, bool]
    profile_name: str
    skipif: str | None
    pyversion: str | None
    expected: ExpectedOutput | None


class GroupPlan(t.NamedTuple):
    """Structurally immutable execution plan for one Sphinx group.

    Attributes
    ----------
    group : str
        Author-facing group name.
    blocks : tuple of ProjectedBlock
        Block recipes in execution order.
    seed : mapping of str to Any
        Initial names copied into each attempt's live mapping.
    """

    group: str
    blocks: tuple[ProjectedBlock, ...]
    seed: t.Mapping[str, t.Any]


Failure: t.TypeAlias = doctest.DocTestFailure | doctest.UnexpectedException


class Counts(t.NamedTuple):
    """Failure, attempt, and skip counts for one block.

    Attributes
    ----------
    failed : int
        Number of mismatches, including failures hidden from detailed reports.
    attempted : int
        Number of examples doctest attempted.
    skipped : int
        Number of examples skipped by inline or block policy.
    """

    failed: int
    attempted: int
    skipped: int


class SkipReason(t.NamedTuple):
    """Structured explanation for a skipped block.

    Attributes
    ----------
    kind : {"skipif", "inline-flag", "pyversion"}
        Policy that skipped the block.
    detail : str
        Gate expression, option name, specifier, or profile explanation.
    """

    kind: t.Literal["skipif", "inline-flag", "pyversion"]
    detail: str


class Passed(t.NamedTuple):
    """Successful block result.

    Attributes
    ----------
    block : ProjectedBlock
        Block that ran.
    counts : Counts
        Failure, attempt, and skip totals.
    """

    block: ProjectedBlock
    counts: Counts


class Failed(t.NamedTuple):
    """Doctest-comparison failures from one block.

    Attributes
    ----------
    block : ProjectedBlock
        Block that ran.
    counts : Counts
        Failure, attempt, and skip totals.
    failures : tuple of Failure
        Failures retained in example order.
    checker : doctest.OutputChecker
        Exact checker instance that compared and must explain the failures.
    """

    block: ProjectedBlock
    counts: Counts
    failures: tuple[Failure, ...]
    checker: doctest.OutputChecker


class Skipped(t.NamedTuple):
    """Block skipped by a run-time policy.

    Attributes
    ----------
    block : ProjectedBlock
        Block that did not run.
    counts : Counts
        Failure, attempt, and skip totals.
    reason : SkipReason
        Structured skip explanation.
    """

    block: ProjectedBlock
    counts: Counts
    reason: SkipReason


class Errored(t.NamedTuple):
    """Infrastructure or gate error from one block.

    Attributes
    ----------
    block : ProjectedBlock
        Block whose execution failed outside doctest comparison.
    error : BaseException
        Original exception retained for the host adapter.
    """

    block: ProjectedBlock
    error: BaseException


BlockResult: t.TypeAlias = Passed | Failed | Skipped | Errored


class GroupResult(t.NamedTuple):
    """Result of one group attempt.

    Attributes
    ----------
    group : str
        Author-facing group name.
    blocks : tuple of BlockResult
        Results in execution order.
    primary : BaseException or None
        Body exception a host should re-raise.
    secondary : tuple of BaseException
        Additional exceptions, such as cleanup errors after body failure.
    """

    group: str
    blocks: tuple[BlockResult, ...]
    primary: BaseException | None
    secondary: tuple[BaseException, ...]
