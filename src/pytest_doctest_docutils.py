"""pytest_doctest_docutils

pytest plugin for doctest w/ reStructuredText and markdown

.. seealso::

   - http://www.sphinx-doc.org/en/stable/ext/doctest.html
   - https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/doctest.py

   This is a derivative of my PR https://github.com/thisch/pytest-sphinx/pull/38 to
   pytest-sphinx (BSD 3-clause), 2022-09-03.
"""
import bdb
import doctest
import logging
import sys
import types
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional, Tuple, Type

import _pytest
import pytest
from _pytest import outcomes
from _pytest.outcomes import OutcomeException
from doctest_docutils import DocutilsDocTestFinder, setup

if TYPE_CHECKING:
    from doctest import _Out

    from _pytest.config.argparsing import Parser
    from _pytest.doctest import DoctestItem


logger = logging.getLogger(__name__)

# Lazy definition of runner class
RUNNER_CLASS = None


def pytest_addoption(parser: "Parser") -> None:
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
    global RUNNER_CLASS

    RUNNER_CLASS = None


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> Optional[Tuple["DocTestDocutilsFile", "_pytest.doctest.DoctestModule"]]:
    config = parent.config
    if file_path.suffix == ".py":
        if config.option.doctestmodules and not any(
            # if not any(
            (
                _pytest.doctest._is_setup_py(file_path),
                _pytest.doctest._is_main_py(file_path),
            )
        ):
            mod: Tuple[
                DocTestDocutilsFile, _pytest.doctest.DoctestModule
            ] = _pytest.doctest.DoctestModule.from_parent(parent, path=file_path)
            return mod
    elif _is_doctest(config, file_path, parent):
        return DocTestDocutilsFile.from_parent(parent, path=file_path)  # type: ignore
    return None


def _is_doctest(config: pytest.Config, path: Path, parent: pytest.Collector) -> bool:
    if path.suffix in (".rst", ".md") and parent.session.isinitpath(path):
        return True
    globs = config.getoption("doctestglob") or ["*.rst", "*.md"]
    return any(path.match(path_pattern=glob) for glob in globs)


def _init_runner_class() -> Type["doctest.DocTestRunner"]:
    import doctest

    class PytestDoctestRunner(doctest.DebugRunner):
        """Runner to collect failures.

        Note that the out variable in this case is a list instead of a
        stdout-like object.
        """

        def __init__(
            self,
            checker: Optional["doctest.OutputChecker"] = None,
            verbose: Optional[bool] = None,
            optionflags: int = 0,
            continue_on_failure: bool = True,
        ) -> None:
            super().__init__(checker=checker, verbose=verbose, optionflags=optionflags)
            self.continue_on_failure = continue_on_failure

        def report_failure(
            self,
            out: "_Out",
            test: "doctest.DocTest",
            example: "doctest.Example",
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
            out: "_Out",
            test: "doctest.DocTest",
            example: "doctest.Example",
            exc_info: Tuple[Type[BaseException], BaseException, types.TracebackType],
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


def _get_runner(
    checker: Optional["doctest.OutputChecker"] = None,
    verbose: Optional[bool] = None,
    optionflags: int = 0,
    continue_on_failure: bool = True,
) -> "doctest.DocTestRunner":
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
    def summarize(  # type: ignore
        self, out: "_Out", verbose: Optional[bool] = None
    ) -> Tuple[int, int]:
        string_io = StringIO()
        old_stdout = sys.stdout
        sys.stdout = string_io
        try:
            res = super().summarize(verbose)
        finally:
            sys.stdout = old_stdout
        out(string_io.getvalue())
        return res

    def _DocTestRunner__patched_linecache_getlines(
        self, filename: str, module_globals: Any = None
    ) -> Any:
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
    def collect(self) -> Iterable["DoctestItem"]:
        setup()

        encoding = self.config.getini("doctest_encoding")
        text = self.path.read_text(encoding)

        # Uses internal doctest module parsing mechanism.
        finder = DocutilsDocTestFinder()

        optionflags = _pytest.doctest.get_optionflags(self)  # type: ignore

        runner = _get_runner(
            verbose=False,
            optionflags=optionflags,
            checker=_pytest.doctest._get_checker(),
            continue_on_failure=_pytest.doctest._get_continue_on_failure(  # type:ignore
                self.config
            ),
        )
        from _pytest.doctest import DoctestItem

        for test in finder.find(
            text,
            str(self.path),
        ):
            if test.examples:  # skip empty doctests
                yield DoctestItem.from_parent(
                    self, name=test.name, runner=runner, dtest=test  # type: ignore
                )
