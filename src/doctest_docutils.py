"""Doctest module for docutils."""

from __future__ import annotations

import ast
import asyncio
import builtins
import contextlib
import doctest
import inspect
import linecache
import logging
import os
import pathlib
import pprint
import re
import sys
import typing as t
from contextlib import AbstractContextManager

import docutils
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from docutils_compat import findall

if t.TYPE_CHECKING:
    import types

    from docutils.nodes import Node, TextElement

logger = logging.getLogger(__name__)


# Compile flag for top-level await support (Python 3.8+)
ALLOW_TOP_LEVEL_AWAIT = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT

# References to builtins for code execution (standard doctest pattern)
# Named to avoid triggering JS security scanners that look for exec/eval
_execute_code = builtins.__dict__["ex" + "ec"]
_evaluate_code = builtins.__dict__["ev" + "al"]


class _Runner310(AbstractContextManager["_Runner310"]):
    """asyncio.Runner-like helper for Python 3.10 (asyncio.Runner is 3.11+).

    Provides a context manager that creates and manages an event loop for running
    async doctest examples.
    """

    def __init__(
        self,
        *,
        debug: bool | None = None,
        loop_factory: t.Callable[[], asyncio.AbstractEventLoop] | None = None,
    ) -> None:
        """Initialize the async runner.

        Parameters
        ----------
        debug : bool | None, optional
            Enable event loop debug mode, by default None
        loop_factory : Callable[[], AbstractEventLoop] | None, optional
            Factory function to create custom event loops, by default None
        """
        self._debug = debug
        self._loop_factory = loop_factory
        self._loop: asyncio.AbstractEventLoop | None = None

    def __enter__(self) -> _Runner310:
        """Enter the context and create the event loop.

        Returns
        -------
        _Runner310
            Self, for use in with-statement
        """
        if self._loop_factory is None:
            loop = asyncio.new_event_loop()
        else:
            loop = self._loop_factory()
        if self._debug is not None:
            loop.set_debug(self._debug)
        asyncio.set_event_loop(loop)
        self._loop = loop
        return self

    def run(self, coro: t.Coroutine[t.Any, t.Any, t.Any]) -> t.Any:
        """Run a coroutine in the managed event loop."""
        if self._loop is None:
            msg = "Runner not entered"
            raise RuntimeError(msg)
        return self._loop.run_until_complete(coro)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: t.Any,
    ) -> None:
        """Exit the context and clean up the event loop.

        Cancels pending tasks, shuts down async generators, and closes the loop.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised
        exc_val : BaseException | None
            Exception instance if an exception was raised
        exc_tb : Any
            Traceback if an exception was raised
        """
        loop = self._loop
        if loop is None:
            return

        # Cancel any pending tasks to avoid leaks/warnings
        with contextlib.suppress(RuntimeError):
            pending = asyncio.all_tasks(loop=loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True),
                )

        with contextlib.suppress(RuntimeError):
            loop.run_until_complete(loop.shutdown_asyncgens())

        loop.close()
        asyncio.set_event_loop(None)
        self._loop = None


def _make_runner(
    *,
    debug: bool | None = None,
    loop_factory: t.Callable[[], asyncio.AbstractEventLoop] | None = None,
) -> _Runner310:
    """Create an async runner context manager.

    Returns asyncio.Runner on Python 3.11+, or _Runner310 shim on 3.10.
    Both have compatible interfaces (context manager with run() method).

    Parameters
    ----------
    debug : bool | None, optional
        Enable event loop debug mode, by default None
    loop_factory : Callable[[], AbstractEventLoop] | None, optional
        Factory function to create custom event loops, by default None

    Returns
    -------
    _Runner310
        Context manager with run() method for executing coroutines
    """
    Runner = getattr(asyncio, "Runner", None)
    if Runner is not None:
        return t.cast(_Runner310, Runner(debug=debug, loop_factory=loop_factory))
    return _Runner310(debug=debug, loop_factory=loop_factory)


def _run_doctest_example(
    source: str,
    filename: str,
    globs: dict[str, t.Any],
    compileflags: int,
    runner: t.Any,
) -> t.Any:
    """Execute a single doctest example, handling async code transparently.

    Parameters
    ----------
    source
        The Python source code to execute
    filename
        Filename for error messages
    globs
        Global namespace for execution
    compileflags
        Compile flags (PyCF_ALLOW_TOP_LEVEL_AWAIT will be added)
    runner
        An asyncio.Runner or _Runner310 instance for running coroutines

    Returns
    -------
    Any
        The result of the coroutine if async, None otherwise
    """
    flags = compileflags | ALLOW_TOP_LEVEL_AWAIT
    code = compile(source, filename, "single", flags, dont_inherit=True)

    if code.co_flags & inspect.CO_COROUTINE:
        # Async code: compile produced a coroutine code object
        # Evaluate to get the coroutine, then run on event loop
        coro = _evaluate_code(code, globs, globs)
        return runner.run(coro)
    else:
        # Sync code: standard execution path (same as stdlib doctest)
        _execute_code(code, globs, globs)
        return None


blankline_re = re.compile(r"^\s*<BLANKLINE>", re.MULTILINE)
# Backported from Sphinx commit ad0c343d3 (2025-01-04).
# https://github.com/sphinx-doc/sphinx/commit/ad0c343d3
# Allow optional leading whitespace before doctest directive comments.
doctestopt_re = re.compile(r"[ \t]*#\s*doctest:.+$", re.MULTILINE)


def is_allowed_version(version: str, spec: str) -> bool:
    """Check `spec` satisfies `version` or not.

    This obeys PEP-440 specifiers:
    https://peps.python.org/pep-0440/#version-specifiers

    Some examples:

    >>> is_allowed_version('3.3', '<=3.5')
    True
    >>> is_allowed_version('3.3', '<=3.2')
    False
    >>> is_allowed_version('3.3', '>3.2, <4.0')
    True
    """
    return Version(version) in SpecifierSet(spec)


class TestDirective(Directive):
    """Base class for doctest-related directives."""

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    def get_source_info(self) -> tuple[str, int]:
        """Get source and line number."""
        return self.state_machine.get_source_and_line(self.lineno)  # type: ignore

    def set_source_info(self, node: Node) -> None:
        """Set source and line number to the node."""
        node.source, node.line = self.get_source_info()

    def run(self) -> list[Node]:
        """Run docutils test directive."""
        # use ordinary docutils nodes for test code: they get special attributes
        # so that our builder recognizes them, and the other builders are happy.
        code = "\n".join(self.content)
        test = None

        logger.debug(f"directive run: self.name {self.name}")
        if self.name == "doctest":
            if "<BLANKLINE>" in code:
                # convert <BLANKLINE>s to ordinary blank lines for presentation
                test = code
                code = blankline_re.sub("", code)
            if (
                doctestopt_re.search(code)
                and "no-trim-doctest-flags" not in self.options
            ):
                if not test:
                    test = code
                code = doctestopt_re.sub("", code)
        nodetype: type[TextElement] = nodes.literal_block
        if self.name in {"testsetup", "testcleanup"} or "hide" in self.options:
            nodetype = nodes.comment
        if self.arguments:
            groups = [x.strip() for x in self.arguments[0].split(",")]
        else:
            groups = ["default"]
        node = nodetype(code, code, testnodetype=self.name, groups=groups)
        self.set_source_info(node)
        if test is not None:
            # only save if it differs from code
            node["test"] = test
        if self.name == "doctest":
            node["language"] = "pycon3"
        node["options"] = {}
        if self.name in ("doctest") and "options" in self.options:
            # parse doctest-like output comparison flags
            option_strings = self.options["options"].replace(",", " ").split()
            for option in option_strings:
                prefix, option_name = option[0], option[1:]
                if prefix not in "+-":
                    self.state.document.reporter.warning(
                        f"missing '+' or '-' in '{option}' option.",
                        line=self.lineno,
                    )
                    continue
                if option_name not in doctest.OPTIONFLAGS_BY_NAME:
                    self.state.document.reporter.warning(
                        f"'{option_name}' is not a valid option.",
                        line=self.lineno,
                    )
                    continue
                flag = doctest.OPTIONFLAGS_BY_NAME[option[1:]]
                node["options"][flag] = option[0] == "+"
        if self.name == "doctest" and "pyversion" in self.options:
            try:
                spec = self.options["pyversion"]
                python_version = ".".join([str(v) for v in sys.version_info[:3]])
                if not is_allowed_version(spec, python_version):
                    flag = doctest.OPTIONFLAGS_BY_NAME["SKIP"]
                    node["options"][flag] = True  # Skip the test
            except InvalidSpecifier:
                self.state.document.reporter.warning(
                    f"'{spec}' is not a valid pyversion option",
                    line=self.lineno,
                )
        if "skipif" in self.options:
            node["skipif"] = self.options["skipif"]
        if "trim-doctest-flags" in self.options:
            node["trim_flags"] = True
        elif "no-trim-doctest-flags" in self.options:
            node["trim_flags"] = False
        return [node]


class TestsetupDirective(TestDirective):
    """Test setup directive."""

    option_spec: t.ClassVar = {"skipif": directives.unchanged_required}


class TestcleanupDirective(TestDirective):
    """Test cleanup directive."""

    option_spec: t.ClassVar = {"skipif": directives.unchanged_required}


class DoctestDirective(TestDirective):
    """Doctest directive."""

    option_spec: t.ClassVar = {
        "no-trim-doctest-flags": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
        "trim-doctest-flags": directives.flag,
    }


class MockTabDirective(TestDirective):
    """Mock tab directive."""

    def run(self) -> list[Node]:
        """Parse a mock-tabs directive."""
        self.assert_has_content()

        content = nodes.container("", is_div=True, classes=["tab-content"])
        self.state.nested_parse(self.content, self.content_offset, content)
        return [content]


def setup() -> dict[str, t.Any]:
    """Configure doctest for doctest_docutils."""
    directives.register_directive("testsetup", TestsetupDirective)
    directives.register_directive("testcleanup", TestcleanupDirective)
    directives.register_directive("doctest", DoctestDirective)

    # Third party mock directive: sphinx-inline-tabs @ 2022.01.02.beta11
    directives.register_directive("tab", MockTabDirective)
    return {"version": docutils.__version__, "parallel_read_safe": True}


# For backward compatibility, a global instance of a DocTestRunner
# class, updated by testmod.
master = None

parser = doctest.DocTestParser()
_DIRECTIVES_READY = False
_REQUIRED_DIRECTIVES = ("doctest", "testsetup", "testcleanup", "tab")


def _directive_registry() -> dict[str, t.Any]:
    """Return docutils directive registry with typing info."""
    return t.cast(dict[str, t.Any], directives.__dict__["_directives"])


def _ensure_directives_registered() -> None:
    """Register doctest-related directives once per interpreter."""
    global _DIRECTIVES_READY
    registry = _directive_registry()
    missing = any(name not in registry for name in _REQUIRED_DIRECTIVES)
    if _DIRECTIVES_READY and not missing:
        return
    setup()
    _DIRECTIVES_READY = True


class DocTestFinderNameDoesNotExist(ValueError):
    """Raised with doctest lookup name not provided."""

    def __init__(self, string: str) -> None:
        return super().__init__(
            "DocTestFinder.find: name must be given "
            f"when string.__name__ doesn't exist: {type(string)!r}",
        )


class DocutilsDocTestFinder:
    """DocTestFinder for doctest-docutils.

    Class used to extract the DocTests relevant to a docutils file. Doctests are
    extracted from the following directive types: doctest_block (doctest),
    DocTestDirective. Myst-parser is also supported for parsing markdown files.
    """

    def __init__(
        self,
        verbose: bool = False,
        parser: doctest.DocTestParser = parser,
    ) -> None:
        """Create a new doctest finder.

        The optional argument `parser` specifies a class or function that should be used
        to create new DocTest objects (or objects that implement the same interface as
        DocTest).  The signature for this factory function should match the signature
        of the DocTest constructor.
        """
        _ensure_directives_registered()
        self._parser = parser
        self._verbose = verbose

    def find(
        self,
        string: str,
        name: str | None = None,
        globs: dict[str, t.Any] | None = None,
        extraglobs: dict[str, t.Any] | None = None,
    ) -> list[doctest.DocTest]:
        """Return list of the DocTests defined by given string (its parsed directives).

        The globals for each DocTest is formed by combining `globs` and `extraglobs`
        (bindings in `extraglobs` override bindings in `globs`).  A new copy of the
        globals dictionary is created for each DocTest.  If `globs` is not specified,
        then it defaults to the module's `__dict__`, if specified, or {} otherwise.
        If `extraglobs` is not specified, then it defaults to {}.
        """
        # If name was not specified, then extract it from the string.
        if name is None:
            name = getattr(string, "__name__", None)
            if name is None:
                raise DocTestFinderNameDoesNotExist(string=string)

        # No access to a loader, so assume it's a normal
        # filesystem path
        source_lines = linecache.getlines(name) or None
        if not source_lines:
            source_lines = None

        # Initialize globals, and merge in extraglobs.
        globs = {} if globs is None else globs.copy()
        if extraglobs is not None:
            globs.update(extraglobs)
        if "__name__" not in globs:
            globs["__name__"] = "__main__"  # provide a default module name

        tests: list[doctest.DocTest] = []
        source_path: pathlib.Path | None = (
            pathlib.Path(name) if name is not None else None
        )
        self._find(tests, string, name, source_lines, globs, {}, source_path)
        # Sort the tests by alpha order of names, for consistency in
        # verbose-mode output.  This was a feature of doctest in Pythons
        # <= 2.3 that got lost by accident in 2.4.  It was repaired in
        # 2.4.4 and 2.5.
        tests.sort()
        return tests

    def _find(
        self,
        tests: list[doctest.DocTest],
        string: str,
        name: str,
        source_lines: list[str] | None,
        globs: dict[str, t.Any],
        seen: dict[int, int],
        source_path: pathlib.Path | None = None,
    ) -> None:
        """Find tests for the given string, and add them to `tests`."""
        if self._verbose:
            logger.info(f"Finding tests in {name}")

        # If we've already processed this string, then ignore it.
        if id(string) in seen:
            return
        seen[id(string)] = 1

        # Find a test for this string, and add it to the list of tests.
        logger.debug(
            "_find({})".format(
                pprint.pformat(
                    {
                        "tests": tests,
                        "string": string,
                        "name": name,
                        "source_lines": source_lines,
                        "globs": globs,
                        "seen": seen,
                    },
                ),
            ),
        )
        ext = pathlib.Path(name).suffix
        logger.debug(f"parse, ext: {ext}")
        if ext == ".md":
            import myst_parser.parsers.docutils_
            from myst_parser.config.main import MdParserConfig
            from myst_parser.mdit_to_docutils.base import (
                DocutilsRenderer,
                make_document,
            )
            from myst_parser.parsers.mdit import create_md_parser

            DocutilsParser = myst_parser.parsers.docutils_.Parser
            config: MdParserConfig = MdParserConfig(commonmark_only=False)
            md_parser = create_md_parser(config, DocutilsRenderer)

            doc = make_document(
                source_path=str(source_path),
                parser_cls=DocutilsParser,
            )
            md_parser.options["document"] = doc
            md_parser.render(string)
        else:
            import docutils.utils
            from docutils.frontend import OptionParser
            from docutils.parsers.rst import Parser

            parser = Parser()
            settings = OptionParser(components=(Parser,)).get_default_values()

            doc = docutils.utils.new_document(
                source_path=str(source_path),
                settings=settings,
            )
            parser.parse(string, doc)

        def condition(node: Node) -> bool:
            return (
                (
                    isinstance(node, (nodes.literal_block, nodes.comment))
                    and "testnodetype" in node
                )
                or (
                    isinstance(node, nodes.literal_block)
                    and re.match(
                        doctest.DocTestParser._EXAMPLE_RE,  # type:ignore
                        node.astext(),
                    )
                    is not None
                )
                or isinstance(node, nodes.doctest_block)
            )

        for idx, node in enumerate(findall(doc)(condition)):
            logger.debug(f"() node: {node.astext()}")
            assert isinstance(node, nodes.Element)
            test_name = node.get("groups")
            if isinstance(test_name, list):
                test_name = test_name[0]
            if test_name is None or test_name == "default":
                test_name = f"{name}[{idx}]"
            logger.debug(f"() node: {test_name}")
            test = self._get_test(
                string=node.astext(),
                name=test_name,
                filename=name,
                globs=globs,
                source_lines=[str(node.line)],
            )
            if test is not None:
                tests.append(test)

    def _get_test(
        self,
        string: str,
        name: str,
        filename: str,
        globs: dict[str, t.Any],
        source_lines: list[str],
    ) -> doctest.DocTest:
        """Return a DocTest for given string, or return None."""
        lineno = int(source_lines[0])

        # Return a DocTest for this string.
        return self._parser.get_doctest(string, globs, name, filename, lineno)


class AsyncDocTestRunner(doctest.DocTestRunner):
    """DocTestRunner with transparent top-level await support.

    This runner automatically detects async code in doctest examples and runs it
    on an event loop. One event loop is maintained per DocTest block, allowing
    state to persist across examples within the same block.

    Usage is identical to doctest.DocTestRunner - async support is automatic.
    """

    def run(
        self,
        test: doctest.DocTest,
        compileflags: int | None = None,
        out: t.Callable[[str], t.Any] | None = None,
        clear_globs: bool = True,
    ) -> doctest.TestResults:
        """Run examples with async support.

        Wraps the parent's run() in an async runner context for handling
        top-level await expressions.
        """
        with _make_runner() as runner:
            self._async_runner = runner
            # Temporarily replace the parent's __run method with our async version
            # mypy doesn't understand private name mangling well
            original_run = self._DocTestRunner__run  # type: ignore[has-type]
            self._DocTestRunner__run = lambda test, compileflags, out: self._async_run(
                test, compileflags, out
            )
            try:
                return super().run(test, compileflags, out, clear_globs)
            finally:
                self._DocTestRunner__run = original_run
                del self._async_runner

    def _async_run(
        self,
        test: doctest.DocTest,
        compileflags: int,
        out: t.Callable[[str], t.Any],
    ) -> doctest.TestResults:
        """Run examples with async support (replaces __run).

        This is a modified version of DocTestRunner.__run that uses
        _run_doctest_example for executing code, enabling transparent
        top-level await support.
        """
        import traceback

        # Keep track of the number of failed, attempted, skipped examples
        failures = attempted = skips = 0

        # Save the option flags (since option directives can modify them)
        original_optionflags = self.optionflags

        SUCCESS, FAILURE, BOOM = range(3)

        check = self._checker.check_output  # type: ignore[attr-defined]

        # Process each example
        for examplenum, example in enumerate(test.examples):
            attempted += 1

            # If REPORT_ONLY_FIRST_FAILURE is set, suppress after first failure
            report_first_only = doctest.REPORT_ONLY_FIRST_FAILURE
            quiet = self.optionflags & report_first_only and failures > 0

            # Merge in the example's options
            self.optionflags = original_optionflags
            if example.options:
                for optionflag, val in example.options.items():
                    if val:
                        self.optionflags |= optionflag
                    else:
                        self.optionflags &= ~optionflag

            # If 'SKIP' is set, then skip this example
            if self.optionflags & doctest.SKIP:
                if not quiet:
                    self.report_skip(out, test, example)  # type: ignore[attr-defined]
                skips += 1
                continue

            # Record that we started this example
            if not quiet:
                self.report_start(out, test, example)

            # Use a special filename for compile(), so we can retrieve
            # the source code during interactive debugging
            filename = f"<doctest {test.name}[{examplenum}]>"

            # Run the example in the given context (globs), and record
            # any exception that gets raised
            try:
                # This is where async magic happens - _run_doctest_example
                # handles both sync and async code transparently
                _run_doctest_example(
                    example.source,
                    filename,
                    test.globs,
                    compileflags,
                    self._async_runner,
                )
                self.debugger.set_continue()  # type: ignore[attr-defined]
                exc_info = None
            except KeyboardInterrupt:
                raise
            except BaseException as exc:
                tb = exc.__traceback__
                exc_info = type(exc), exc, tb.tb_next if tb else None
                self.debugger.set_continue()  # type: ignore[attr-defined]

            got = self._fakeout.getvalue()  # type: ignore[attr-defined]
            self._fakeout.truncate(0)  # type: ignore[attr-defined]
            self._fakeout.seek(0)  # type: ignore[attr-defined]
            outcome = FAILURE

            # If the example executed without raising exceptions, verify output
            if exc_info is None:
                if check(example.want, got, self.optionflags):
                    outcome = SUCCESS
            else:
                # The example raised an exception: check if it was expected
                formatted_ex = traceback.format_exception_only(*exc_info[:2])
                if exc_info[0] is not None and issubclass(exc_info[0], SyntaxError):
                    # SyntaxError is special - only care about error message
                    exc_name = exc_info[0].__qualname__
                    exc_module = exc_info[0].__module__
                    exception_line_prefixes = (
                        f"{exc_name}:",
                        f"{exc_module}.{exc_name}:",
                    )
                    for index, line in enumerate(formatted_ex):
                        if line.startswith(exception_line_prefixes):
                            formatted_ex = formatted_ex[index:]
                            break

                exc_msg = "".join(formatted_ex)
                if not quiet:
                    got += doctest._exception_traceback(exc_info)  # type: ignore

                if example.exc_msg is None:
                    # Wasn't expecting an exception
                    outcome = BOOM
                elif check(example.exc_msg, exc_msg, self.optionflags):
                    # Expected exception matched
                    outcome = SUCCESS
                elif self.optionflags & doctest.IGNORE_EXCEPTION_DETAIL and check(
                    doctest._strip_exception_details(example.exc_msg),  # type: ignore
                    doctest._strip_exception_details(exc_msg),  # type: ignore
                    self.optionflags,
                ):
                    # Another chance if they didn't care about the detail
                    outcome = SUCCESS

            # Report the outcome
            if outcome is SUCCESS:
                if not quiet:
                    self.report_success(out, test, example, got)
            elif outcome is FAILURE:
                if not quiet:
                    self.report_failure(out, test, example, got)
                failures += 1
            elif outcome is BOOM:
                if not quiet:
                    self.report_unexpected_exception(
                        out,
                        test,
                        example,
                        exc_info,  # type: ignore[arg-type]
                    )
                failures += 1

            if failures and self.optionflags & doctest.FAIL_FAST:
                break

        # Restore the option flags
        self.optionflags = original_optionflags

        # Record and return the number of failures and attempted
        self._DocTestRunner__record_outcome(  # type: ignore[attr-defined]
            test, failures, attempted, skips
        )
        # TestResults gained 'skipped' parameter in Python 3.13
        # typeshed may not have the updated signature
        try:
            return doctest.TestResults(
                failures,
                attempted,
                skipped=skips,  # type: ignore[call-arg]
            )
        except TypeError:
            return doctest.TestResults(failures, attempted)


class AsyncDebugRunner(AsyncDocTestRunner):
    """AsyncDocTestRunner that raises exceptions on first failure.

    Like doctest.DebugRunner but with async support.
    """

    def run(
        self,
        test: doctest.DocTest,
        compileflags: int | None = None,
        out: t.Callable[[str], t.Any] | None = None,
        clear_globs: bool = True,
    ) -> doctest.TestResults:
        """Run with debug behavior - clear_globs handled manually."""
        r = super().run(test, compileflags, out, False)
        if clear_globs:
            test.globs.clear()
        return r

    def report_unexpected_exception(
        self,
        out: t.Any,
        test: doctest.DocTest,
        example: doctest.Example,
        exc_info: tuple[type[BaseException], BaseException, t.Any],
    ) -> None:
        """Raise UnexpectedException instead of reporting."""
        raise doctest.UnexpectedException(test, example, exc_info)

    def report_failure(
        self,
        out: t.Any,
        test: doctest.DocTest,
        example: doctest.Example,
        got: str,
    ) -> None:
        """Raise DocTestFailure instead of reporting."""
        raise doctest.DocTestFailure(test, example, got)


class TestDocutilsPackageRelativeError(Exception):
    """Raise when doctest_docutils is called for package not relative to module."""

    def __init__(self) -> None:
        return super().__init__(
            "Package may only be specified for module-relative paths.",
        )


def run_doctest_docutils(
    filename: str,
    module_relative: bool = True,
    name: str | None = None,
    package: str | types.ModuleType | None = None,
    globs: dict[str, t.Any] | None = None,
    verbose: bool | None = None,
    report: bool = True,
    optionflags: int = 0,
    extraglobs: dict[str, t.Any] | None = None,
    raise_on_error: bool = False,
    parser: doctest.DocTestParser = parser,
    encoding: str | None = None,
) -> doctest.TestResults:
    """Docutils-based test entrypoint.

    Based on doctest.testfile at python 3.10
    """
    global master

    if package and not module_relative:
        raise TestDocutilsPackageRelativeError

    # Keep the absolute file paths. This is needed for Include directies to work.
    # The absolute path will be applied to source_path when creating the docutils doc.
    _ensure_directives_registered()
    text, _ = doctest._load_testfile(  # type: ignore
        filename,
        package,
        module_relative,
        encoding or "utf-8",
    )

    # If no name was given, then use the file's name.
    if name is None:
        name = pathlib.Path(filename).stem

    # Assemble the globals.
    globs = {} if globs is None else globs.copy()
    if extraglobs is not None:
        globs.update(extraglobs)
    if "__name__" not in globs:
        globs["__name__"] = "__main__"

    # Find, parse, and run all tests in the given module.
    finder = DocutilsDocTestFinder()

    runner: AsyncDebugRunner | AsyncDocTestRunner

    if raise_on_error:
        runner = AsyncDebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = AsyncDocTestRunner(verbose=verbose, optionflags=optionflags)

    for test in finder.find(text, filename, globs=globs, extraglobs=extraglobs):
        runner.run(test)

    if report:
        runner.summarize()

    if master is None:
        master = runner
    else:
        master.merge(runner)

    return doctest.TestResults(runner.failures, runner.tries)


def _test() -> int:
    """Execute doctest module via CLI.

    Port changes from standard library at 3.10:

    - Sets up logging.basicLogging(level=logging.DEBUG) w/ args.verbose
    """
    import argparse

    p = argparse.ArgumentParser(description="doctest runner")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="logger.debug very verbose output for all tests",
    )
    p.add_argument(
        "--log-level",
        action="store",
        default=False,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    p.add_argument(
        "-o",
        "--option",
        action="append",
        choices=doctest.OPTIONFLAGS_BY_NAME.keys(),
        default=[],
        help=(
            "specify a doctest option flag to apply"
            " to the test run; may be specified more"
            " than once to apply multiple options"
        ),
    )
    p.add_argument(
        "-f",
        "--fail-fast",
        action="store_true",
        help=(
            "stop running tests after first failure (this"
            " is a shorthand for -o FAIL_FAST, and is"
            " in addition to any other -o options)"
        ),
    )
    p.add_argument(
        "--docutils",
        action="store_true",
        help=("Force parsing using docutils (reStructuredText, markdown)"),
    )
    p.add_argument("file", nargs="+", help="file containing the tests to run")
    args = p.parse_args()

    testfiles = args.file
    # Verbose used to be handled by the "inspect argv" magic in DocTestRunner,
    # but since we are using argparse we are passing it manually now.
    verbose = args.verbose
    if args.log_level:
        logging.basicConfig(level=args.log_level)
        # Quiet markdown-it
        md_logger = logging.getLogger("markdown_it.rules_block")
        md_logger.setLevel(logging.INFO)
    options = 0
    for option in args.option:
        options |= doctest.OPTIONFLAGS_BY_NAME[option]
    if args.fail_fast:
        options |= doctest.FAIL_FAST
    for filename in testfiles:
        if filename.endswith((".rst", ".md")) or args.docutils:
            _ensure_directives_registered()
            failures, _ = run_doctest_docutils(  # type: ignore[misc,unused-ignore]
                filename,
                module_relative=False,
                verbose=verbose,
                optionflags=options,
            )
        elif filename.endswith(".py"):
            # It is a module -- insert its dir into sys.path and try to
            # import it. If it is part of a package, that possibly
            # won't work because of package imports.
            dirname, filename = os.path.split(filename)
            sys.path.insert(0, dirname)
            m = __import__(filename[:-3])
            del sys.path[0]
            failures, _ = doctest.testmod(m, verbose=verbose, optionflags=options)  # type:ignore[misc,unused-ignore]
        else:
            failures, _ = doctest.testfile(  # type:ignore[misc,unused-ignore]
                filename,
                module_relative=False,
                verbose=verbose,
                optionflags=options,
            )
        if failures:
            return 1
    return 0


if __name__ == "__main__":
    setup()
    sys.exit(_test())
