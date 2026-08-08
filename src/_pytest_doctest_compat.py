"""Quarantine pytest's private doctest APIs.

The public functions in this module are the only boundary at which the
``pytest_doctest_docutils`` adapter should depend on ``_pytest.doctest``.
"""

from __future__ import annotations

import collections.abc
import doctest
import traceback
import typing as t

import pytest
from _pytest import doctest as pytest_doctest
from _pytest._code import ExceptionInfo
from _pytest._code.code import ReprFileLocation, TerminalRepr

DoctestTextfile = pytest_doctest.DoctestTextfile
MultipleDoctestFailures = pytest_doctest.MultipleDoctestFailures


class _OptionflagsContext:
    """Present the option interface expected by pytest 7 through 9.

    Attributes
    ----------
    config : pytest.Config
        Configuration exposed for pytest 7's collector-like call shape.
    """

    def __init__(self, config: pytest.Config) -> None:
        """Store the pytest configuration.

        Parameters
        ----------
        config : pytest.Config
            Configuration whose doctest flags are requested.

        Examples
        --------
        The compatibility object retains the exact config object.

        >>> marker = object()
        >>> context = _OptionflagsContext(t.cast(pytest.Config, marker))
        >>> context.config is marker
        True
        """
        self.config = config

    def getini(self, name: str) -> object:
        """Delegate ini access for pytest 8 and newer.

        Parameters
        ----------
        name : str
            Ini option name.

        Returns
        -------
        object
            Parsed ini value.

        Examples
        --------
        >>> class Config:
        ...     def getini(self, name: str) -> object:
        ...         return name
        >>> context = _OptionflagsContext(t.cast(pytest.Config, Config()))
        >>> context.getini("doctest_optionflags")
        'doctest_optionflags'
        """
        return self.config.getini(name)


def get_checker() -> doctest.OutputChecker:
    """Return pytest's extended doctest output checker.

    Returns
    -------
    doctest.OutputChecker
        Checker supporting pytest's ``ALLOW_*`` and ``NUMBER`` flags.

    Examples
    --------
    >>> isinstance(get_checker(), doctest.OutputChecker)
    True
    """
    return pytest_doctest._get_checker()


def get_continue_on_failure(config: pytest.Config) -> bool:
    """Return pytest's resolved continue-on-failure policy.

    Parameters
    ----------
    config : pytest.Config
        Active pytest configuration.

    Returns
    -------
    bool
        False when pdb requires stopping at the first failure.

    Examples
    --------
    The result is always a concrete boolean for a configured session.

    >>> callable(get_continue_on_failure)
    True
    """
    return pytest_doctest._get_continue_on_failure(config)


def get_optionflags(config: pytest.Config) -> int:
    """Return doctest option flags across pytest 7 through 9.

    Pytest 7 expects a collector-like object with ``.config``; pytest 8 and
    newer expect ``Config`` directly. The compatibility context supports both.

    Parameters
    ----------
    config : pytest.Config
        Active pytest configuration.

    Returns
    -------
    int
        Bitwise combination of configured doctest flags.

    Examples
    --------
    >>> callable(get_optionflags)
    True
    """
    context = _OptionflagsContext(config)
    return pytest_doctest.get_optionflags(context)  # type: ignore[arg-type]


def make_multiple_failures(
    failures: collections.abc.Sequence[
        doctest.DocTestFailure | doctest.UnexpectedException
    ],
) -> BaseException:
    """Build pytest's aggregate doctest failure across its narrow annotation.

    Pytest's runner stores both ordinary and unexpected doctest failures, while
    the private exception constructor is annotated for ordinary failures only.

    Parameters
    ----------
    failures : sequence of doctest failures
        Failures retained in source order.

    Returns
    -------
    BaseException
        Pytest's aggregate failure carrying the original sequence.

    Examples
    --------
    >>> callable(make_multiple_failures)
    True
    """
    constructor = t.cast(t.Any, MultipleDoctestFailures)
    return t.cast(BaseException, constructor(failures))


def repr_failure_with_checkers(
    item: pytest.DoctestItem,
    excinfo: ExceptionInfo[BaseException],
    checkers: t.Mapping[int, doctest.OutputChecker],
) -> str | TerminalRepr | None:
    """Render doctest failures with their comparison-time checkers.

    Parameters
    ----------
    item : pytest.DoctestItem
        Item whose configuration selects pytest's report style.
    excinfo : pytest.ExceptionInfo
        Failure raised by the item.
    checkers : mapping of int to doctest.OutputChecker
        Checker instances indexed by ``id(failure)``.

    Returns
    -------
    str, pytest.TerminalRepr, or None
        Pytest's doctest representation, or ``None`` for non-doctest errors.

    Examples
    --------
    >>> callable(repr_failure_with_checkers)
    True
    """
    failures: (
        collections.abc.Sequence[doctest.DocTestFailure | doctest.UnexpectedException]
        | None
    ) = None
    if isinstance(
        excinfo.value,
        (doctest.DocTestFailure, doctest.UnexpectedException),
    ):
        failures = [excinfo.value]
    elif isinstance(excinfo.value, MultipleDoctestFailures):
        failures = t.cast(
            collections.abc.Sequence[
                doctest.DocTestFailure | doctest.UnexpectedException
            ],
            excinfo.value.failures,
        )
    if failures is None:
        return None

    reprlocation_lines: list[tuple[t.Any, list[str]]] = []
    report_choice = pytest_doctest._get_report_choice(
        item.config.getoption("doctestreport"),
    )
    for failure in failures:
        example = failure.example
        test = failure.test
        lineno = None if test.lineno is None else test.lineno + example.lineno + 1
        reprlocation = ReprFileLocation(
            t.cast(str, test.filename),
            lineno,  # type: ignore[arg-type]
            type(failure).__name__,
        )
        if lineno is not None:
            assert test.docstring is not None
            assert test.lineno is not None
            lines = [
                f"{index + test.lineno + 1:03d} {line}"
                for index, line in enumerate(test.docstring.splitlines(False))
            ]
            lines = lines[max(example.lineno - 9, 0) : example.lineno + 1]
        else:
            lines = [
                "EXAMPLE LOCATION UNKNOWN, not showing all tests of that example",
            ]
            indent = ">>>"
            for line in example.source.splitlines():
                lines.append(f"??? {indent} {line}")
                indent = "..."

        if isinstance(failure, doctest.DocTestFailure):
            checker = checkers[id(failure)]
            lines.extend(
                checker.output_difference(
                    example,
                    failure.got,
                    report_choice,
                ).split("\n"),
            )
        else:
            inner_excinfo = ExceptionInfo.from_exc_info(
                failure.exc_info,
            )
            lines.append(f"UNEXPECTED EXCEPTION: {inner_excinfo.value!r}")
            lines.extend(
                line.strip("\n")
                for line in traceback.format_exception(*failure.exc_info)
            )
        reprlocation_lines.append((reprlocation, lines))
    return pytest_doctest.ReprFailDoctest(reprlocation_lines)


def disable_output_capturing_for_darwin(item: pytest.DoctestItem) -> None:
    """Apply pytest's Darwin doctest capture workaround to an item.

    Parameters
    ----------
    item : pytest.DoctestItem
        Item about to execute doctest examples.

    Examples
    --------
    >>> callable(disable_output_capturing_for_darwin)
    True
    """
    item._disable_output_capturing_for_darwin()


__all__ = [
    "DoctestTextfile",
    "MultipleDoctestFailures",
    "disable_output_capturing_for_darwin",
    "get_checker",
    "get_continue_on_failure",
    "get_optionflags",
    "make_multiple_failures",
    "repr_failure_with_checkers",
]
