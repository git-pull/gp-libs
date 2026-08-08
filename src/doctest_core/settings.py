"""Immutable settings resolved before doctest-core pipeline stages."""

from __future__ import annotations

import typing as t


class ParseSettings(t.NamedTuple):
    """Settings for markup parsing and extraction.

    Attributes
    ----------
    suppressed_diagnostics : frozenset of str
        Diagnostic codes omitted from the returned parse result.

    >>> ParseSettings().suppressed_diagnostics
    frozenset({'docutils.unknown-role'})
    """

    suppressed_diagnostics: frozenset[str] = frozenset({"docutils.unknown-role"})


class ProjectionSettings(t.NamedTuple):
    """Settings for pure block-to-group projection.

    Attributes
    ----------
    ungrouped : {"default", "block"}
        Put unlabelled blocks in the shared ``default`` group or isolate them.

    >>> ProjectionSettings().ungrouped
    'default'
    """

    ungrouped: t.Literal["default", "block"] = "default"


class RunSettings(t.NamedTuple):
    """Serializable policy for one doctest run.

    Attributes
    ----------
    optionflags : int
        Runner-level doctest option bitmask.
    continue_on_failure : bool
        Retain later failures from the same block after a mismatch.
    checker_name : str
        Output-checker registration selected for the run.

    >>> (RunSettings().continue_on_failure, RunSettings().checker_name)
    (True, 'stdlib')
    """

    optionflags: int = 0
    continue_on_failure: bool = True
    checker_name: str = "stdlib"
