"""Public structural contracts for doctest-core extensions."""

from __future__ import annotations

import contextlib
import dataclasses
import doctest
import pathlib
import typing as t

from docutils import nodes

from .model import BlockKind, Diagnostic, Failure
from .settings import ParseSettings


class Provider(t.NamedTuple):
    """Identity attached to every contributed capability.

    Attributes
    ----------
    name : str
        Stable provider name.
    version : str or None
        Provider version when one is available.

    >>> Provider("example", "1").name
    'example'
    """

    name: str
    version: str | None


T = t.TypeVar("T")


@dataclasses.dataclass(frozen=True, slots=True)
class Registration(t.Generic[T]):
    """One immutable, attributed registry entry.

    Attributes
    ----------
    name : str
        Case-sensitive registration name.
    value : T
        Registered capability.
    provider : Provider
        Contributor that supplied the value.
    """

    name: str
    value: T
    provider: Provider


class RuntimeOutcome(t.NamedTuple):
    """Outcome returned by an execution runtime.

    Attributes
    ----------
    results : doctest.TestResults
        Standard attempted and failed totals.
    failures : tuple of Failure
        Failures retained for host-native reporting.
    skipped : int
        Examples reached and skipped by the runtime.
    """

    results: doctest.TestResults
    failures: tuple[Failure, ...]
    skipped: int


class ExceptionPolicy(t.Protocol):
    """Classify exceptions that must escape a runtime's doctest loop."""

    def should_propagate(self, error: BaseException) -> bool:
        """Return whether ``error`` belongs to the embedding host.

        >>> isinstance(KeyboardInterrupt(), BaseException)
        True
        """
        ...

    def is_abort(self, error: BaseException) -> bool:
        """Return whether ``error`` must outrank every recorded outcome.

        >>> isinstance(KeyboardInterrupt(), BaseException)
        True
        """
        ...


class RuntimeSettings(t.NamedTuple):
    """Resolved objects and policy used by one execution runtime.

    Attributes
    ----------
    optionflags : int
        Runner-level doctest option bitmask.
    continue_on_failure : bool
        Continue after an example mismatch.
    checker : doctest.OutputChecker
        Fresh checker used for comparison and explanation.
    exception_policy : ExceptionPolicy
        Host-neutral classifier for exceptions that must propagate.
    """

    optionflags: int
    continue_on_failure: bool
    checker: doctest.OutputChecker
    exception_policy: ExceptionPolicy


class CheckerFactory(t.Protocol):
    """Construct a fresh output checker for an execution runtime."""

    def __call__(self) -> doctest.OutputChecker:
        r"""Return a checker used for comparison and failure explanation.

        >>> doctest.OutputChecker().check_output("42\n", "42\n", 0)
        True
        """
        ...


class ExecutionRuntime(t.Protocol):
    """Attempt-local executor for materialized stock doctests."""

    def run(self, test: doctest.DocTest) -> RuntimeOutcome:
        """Execute ``test`` without clearing its shared globals.

        >>> test = doctest.DocTest([], {}, "example", "example.rst", 0, "")
        >>> test.name
        'example'
        """
        ...


class ExecutionProfile(t.Protocol):
    """Immutable factory for attempt-local execution runtimes."""

    def open(
        self,
        settings: RuntimeSettings,
    ) -> contextlib.AbstractContextManager[ExecutionRuntime]:
        """Open a runtime whose resources live for one group attempt.

        >>> issubclass(contextlib.AbstractContextManager, object)
        True
        """
        ...


class DocumentParser(t.Protocol):
    """Parse one markup language into a docutils document."""

    suffixes: t.ClassVar[frozenset[str]]

    def parse(
        self,
        text: str,
        path: pathlib.Path,
        *,
        settings: ParseSettings,
    ) -> tuple[nodes.document, tuple[Diagnostic, ...]]:
        """Parse ``text`` while retaining normalized diagnostics.

        >>> pathlib.Path("guide.rst").suffix
        '.rst'
        """
        ...


class Registrar(t.Protocol):
    """Provider-bound mutation surface available during contribution."""

    def add_block_kind(
        self,
        name: str,
        kind: BlockKind,
        *,
        replace: bool = False,
    ) -> None:
        """Register a block kind.

        >>> BlockKind.__name__
        'BlockKind'
        """
        ...

    def add_document_parser(
        self,
        name: str,
        parser: DocumentParser,
        *,
        replace: bool = False,
    ) -> None:
        """Register a document parser and its suffix claims.

        >>> ".rst" in frozenset({".rst"})
        True
        """
        ...

    def add_execution_profile(
        self,
        name: str,
        profile: ExecutionProfile,
        *,
        replace: bool = False,
    ) -> None:
        """Register an execution-profile factory.

        >>> "prompt".islower()
        True
        """
        ...

    def add_output_checker(
        self,
        name: str,
        factory: CheckerFactory,
        *,
        replace: bool = False,
    ) -> None:
        """Register an output-checker factory.

        >>> callable(doctest.OutputChecker)
        True
        """
        ...


class Contributor(t.Protocol):
    """Host-neutral source of attributed registry entries."""

    provider: Provider

    def contribute(self, registrar: Registrar) -> None:
        """Add capabilities through the provider-bound ``registrar``.

        >>> Provider("example", None).version is None
        True
        """
        ...
