"""pytest plugin for doctest w/ reStructuredText and markdown.

.. seealso::

   - http://www.sphinx-doc.org/en/stable/ext/doctest.html
   - https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/doctest.py

   This is a derivative of my PR https://github.com/thisch/pytest-sphinx/pull/38 to
   pytest-sphinx (BSD 3-clause), 2022-09-03.
"""

from __future__ import annotations

import bdb
import doctest
import io
import logging
import sys
import typing as t

import _pytest
import pytest
from _pytest import outcomes
from _pytest.outcomes import OutcomeException

from doctest_docutils import DocutilsDocTestFinder, setup

if t.TYPE_CHECKING:
    import pathlib
    import types
    from collections.abc import Iterable
    from doctest import _Out

    from _pytest.config.argparsing import Parser
    from _pytest.doctest import DoctestItem


logger = logging.getLogger(__name__)

# Lazy definition of runner class
RUNNER_CLASS = None


def pytest_addoption(parser: Parser) -> None:
    """Add options to py.test for doctest_docutils."""
    group = parser.getgroup("collect")
    group.addoption(
        "--doctest-docutils-modules",
        action="store_true",
        default=False,
        help="run doctest-doctests in .py modules (pass-through to pytest-doctest)",
        dest="doctestmodules",
    )
    group.addoption(
        "--no-doctest-docutils-modules",
        action="store_false",
        help="disable doctest-doctests in .py modules (pass-through to pytest-doctest)",
        dest="doctestmodules",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Disable pytest.doctest to prevent running tests twice.

    Todo: Find a way to make these plugins cooperate without collecting twice.
    """
    if config.pluginmanager.has_plugin("doctest"):
        config.pluginmanager.set_blocked("doctest")


def pytest_unconfigure() -> None:
    """Unconfigure hook for pytest-doctest-docutils."""
    global RUNNER_CLASS

    RUNNER_CLASS = None


def pytest_collect_file(
    file_path: pathlib.Path,
    parent: pytest.Collector,
) -> DocTestDocutilsFile | _pytest.doctest.DoctestModule | None:
    """Test collector for pytest-doctest-docutils."""
    config = parent.config
    if file_path.suffix == ".py":
        if config.option.doctestmodules and not any(
            # if not any(
            (
                _pytest.doctest._is_setup_py(file_path),
                _pytest.doctest._is_main_py(file_path),
            ),
        ):
            mod: DocTestDocutilsFile | _pytest.doctest.DoctestModule = (
                _pytest.doctest.DoctestModule.from_parent(parent, path=file_path)
            )
            return mod
    elif _is_doctest(config, file_path, parent):
        return DocTestDocutilsFile.from_parent(parent, path=file_path)
    return None


def _is_doctest(
    config: pytest.Config,
    path: pathlib.Path,
    parent: pytest.Collector,
) -> bool:
    if path.suffix in {".rst", ".md"} and parent.session.isinitpath(path):
        return True
    globs = config.getoption("doctestglob") or ["*.rst", "*.md"]
    return any(path.match(path_pattern=glob) for glob in globs)


def _init_runner_class() -> type[doctest.DocTestRunner]:
    import doctest

    class PytestDoctestRunner(doctest.DebugRunner):
        """Runner to collect failures.

        Note that the out variable in this case is a list instead of a
        stdout-like object.
        """

        def __init__(
            self,
            checker: doctest.OutputChecker | None = None,
            verbose: bool | None = None,
            optionflags: int = 0,
            continue_on_failure: bool = True,
        ) -> None:
            super().__init__(checker=checker, verbose=verbose, optionflags=optionflags)
            self.continue_on_failure = continue_on_failure

        def report_failure(
            self,
            out: _Out,
            test: doctest.DocTest,
            example: doctest.Example,
            got: str,
        ) -> None:
            failure = doctest.DocTestFailure(test, example, got)
            if self.continue_on_failure:
                assert isinstance(out, list)
                out.append(failure)
            else:
                raise failure

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
            if isinstance(exc_info[1], OutcomeException):
                raise exc_info[1]
            if isinstance(exc_info[1], bdb.BdbQuit):
                outcomes.exit("Quitting debugger")
            failure = doctest.UnexpectedException(test, example, exc_info)
            if self.continue_on_failure:
                assert isinstance(out, list)
                out.append(failure)
            else:
                raise failure

    return PytestDoctestRunner


def _get_allow_unicode_flag() -> int:
    """Register and return the ALLOW_UNICODE flag."""
    import doctest

    return doctest.register_optionflag("ALLOW_UNICODE")


def _get_allow_bytes_flag() -> int:
    """Register and return the ALLOW_BYTES flag."""
    import doctest

    return doctest.register_optionflag("ALLOW_BYTES")


def _get_number_flag() -> int:
    """Register and return the NUMBER flag."""
    import doctest

    return doctest.register_optionflag("NUMBER")


def _get_flag_lookup() -> dict[str, int]:
    import doctest

    return {
        "DONT_ACCEPT_TRUE_FOR_1": doctest.DONT_ACCEPT_TRUE_FOR_1,
        "DONT_ACCEPT_BLANKLINE": doctest.DONT_ACCEPT_BLANKLINE,
        "NORMALIZE_WHITESPACE": doctest.NORMALIZE_WHITESPACE,
        "ELLIPSIS": doctest.ELLIPSIS,
        "IGNORE_EXCEPTION_DETAIL": doctest.IGNORE_EXCEPTION_DETAIL,
        "COMPARISON_FLAGS": doctest.COMPARISON_FLAGS,
        "ALLOW_UNICODE": _get_allow_unicode_flag(),
        "ALLOW_BYTES": _get_allow_bytes_flag(),
        "NUMBER": _get_number_flag(),
    }


def get_optionflags(config: pytest.Config) -> int:
    """Fetch optionflags from pytest configuration.

    Extracted from pytest.doctest 8.0 (license: MIT).
    """
    optionflags = config.getini("doctest_optionflags")
    # It takes this rocket surgery to satisfy mypy
    optionflags_str = (
        [str(i) for i in optionflags]
        if isinstance(optionflags, list)
        and all(
            isinstance(
                item,
                str,
            )
            for item in optionflags
        )
        else []
    )

    flag_lookup_table = _get_flag_lookup()
    flag_acc = 0
    for flag in optionflags_str:
        flag_acc |= flag_lookup_table[flag]
    return flag_acc


def _get_runner(
    checker: doctest.OutputChecker | None = None,
    verbose: bool | None = None,
    optionflags: int = 0,
    continue_on_failure: bool = True,
) -> doctest.DocTestRunner:
    # We need this in order to do a lazy import on doctest
    global RUNNER_CLASS
    if RUNNER_CLASS is None:
        RUNNER_CLASS = _init_runner_class()
    # Type ignored because the continue_on_failure argument is only defined on
    # PytestDoctestRunner, which is lazily defined so can't be used as a type.
    return RUNNER_CLASS(  # type: ignore
        checker=checker,
        verbose=verbose,
        optionflags=optionflags,
        continue_on_failure=continue_on_failure,
    )


class DocutilsDocTestRunner(doctest.DocTestRunner):
    """DocTestRunner for doctest_docutils."""

    def summarize(  # type: ignore
        self,
        out: _Out,
        verbose: bool | None = None,
    ) -> tuple[int, int]:
        """Summarize the test runs."""
        string_io = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = string_io
        try:
            res = super().summarize(verbose)
        finally:
            sys.stdout = old_stdout
        out(string_io.getvalue())
        return res  # type:ignore[return-value,unused-ignore]

    def _DocTestRunner__patched_linecache_getlines(
        self,
        filename: str,
        module_globals: t.Any = None,
    ) -> t.Any:
        # this is overridden from DocTestRunner adding the try-except below
        m = self._DocTestRunner__LINECACHE_FILENAME_RE.match(filename)  # type: ignore
        if m and m.group("name") == self.test.name:
            try:
                example = self.test.examples[int(m.group("examplenum"))]
            # because we compile multiple doctest blocks with the same name
            # (viz. the group name) this might, for outer stack frames in a
            # traceback, get the wrong test which might not have enough examples
            except IndexError:
                pass
            else:
                return example.source.splitlines(True)
        return self.save_linecache_getlines(filename, module_globals)  # type: ignore


class DocTestDocutilsFile(pytest.Module):
    """Pytest module for doctest_docutils."""

    obj = None  # Fix pytest-asyncio issue. #46, pytest-asyncio#872

    def collect(self) -> Iterable[DoctestItem]:
        """Collect tests for pytest module."""
        setup()

        encoding = self.config.getini("doctest_encoding")
        text = self.path.read_text(encoding)

        # Uses internal doctest module parsing mechanism.
        finder = DocutilsDocTestFinder()

        optionflags = get_optionflags(self.config)

        runner = _get_runner(
            verbose=False,
            optionflags=optionflags,
            checker=_pytest.doctest._get_checker(),
            continue_on_failure=_pytest.doctest._get_continue_on_failure(self.config),
        )
        from _pytest.doctest import DoctestItem

        for test in finder.find(
            text,
            str(self.path),
        ):
            if test.examples:  # skip empty doctests
                yield DoctestItem.from_parent(
                    self,  # type: ignore
                    name=test.name,
                    runner=runner,
                    dtest=test,
                )
