"""Doctest module for docutils."""

from __future__ import annotations

import doctest
import logging
import os
import pathlib
import re
import sys
import types
import typing as t

import docutils
from docutils.parsers.rst import directives
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

import doctest_core
from doctest_core.markup import (
    DoctestDirective as _CoreDoctestDirective,
    MockTabDirective as _CoreMockTabDirective,
    TestcleanupDirective as _CoreTestcleanupDirective,
    TestsetupDirective as _CoreTestsetupDirective,
    _TestDirective as _CoreTestDirective,
)

if t.TYPE_CHECKING:
    from docutils.nodes import Node

logger = logging.getLogger(__name__)


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


class TestDirective(_CoreTestDirective):
    """Compatibility base for doctest-related directives."""

    __test__ = False

    def get_source_info(self) -> tuple[str, int]:
        """Get source and line number."""
        return self.state_machine.get_source_and_line(self.lineno)  # type: ignore

    def set_source_info(self, node: Node) -> None:
        """Set source and line number to the node."""
        node.source, node.line = self.get_source_info()


class TestsetupDirective(_CoreTestsetupDirective, TestDirective):
    """Compatibility name for the core ``testsetup`` directive."""


class TestcleanupDirective(_CoreTestcleanupDirective, TestDirective):
    """Compatibility name for the core ``testcleanup`` directive."""


class DoctestDirective(_CoreDoctestDirective, TestDirective):
    """Compatibility name for the core ``doctest`` directive."""


class MockTabDirective(_CoreMockTabDirective, TestDirective):
    """Compatibility name for the core mock tab directive."""


def setup() -> dict[str, t.Any]:
    """Configure doctest for doctest_docutils."""
    directives.register_directive("testsetup", TestsetupDirective)
    directives.register_directive("testcleanup", TestcleanupDirective)
    directives.register_directive("doctest", DoctestDirective)

    # Third party mock directive: sphinx-inline-tabs @ 2022.01.02.beta11
    directives.register_directive("tab", MockTabDirective)
    doctest_core.ensure_directives_registered()
    return {"version": docutils.__version__, "parallel_read_safe": True}


# For backward compatibility, a global runner updated by ``testdocutils``.
master: doctest.DocTestRunner | None = None

parser = doctest.DocTestParser()


def _ensure_directives_registered() -> None:
    """Register missing core directives without replacing another owner."""
    doctest_core.ensure_directives_registered()


class DocTestFinderNameDoesNotExist(ValueError):
    """Raised with doctest lookup name not provided."""

    def __init__(self, string: str) -> None:
        super().__init__(
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
        self._find(tests, string, name, None, globs, {}, source_path)
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
            logger.info("finding tests in %s", name)

        # If we've already processed this string, then ignore it.
        if id(string) in seen:
            return
        seen[id(string)] = 1
        del source_lines
        parse_path = source_path or pathlib.Path(name)
        if parse_path.suffix not in {".md", ".rst", ".txt"}:
            parse_path = parse_path.with_suffix(".rst")
        parsed = doctest_core.parse_document(string, parse_path)
        for block in parsed.blocks:
            test_name = self._compatibility_name(block, name)
            test = self._get_test(
                string=block.source,
                name=test_name,
                filename=str(block.path),
                globs=globs,
                source_lines=[
                    str(0 if block.line is None else max(block.line - 1, 0)),
                ],
            )
            self._apply_block_options(test, block)
            tests.append(test)

    @staticmethod
    def _compatibility_name(block: doctest_core.ParsedBlock, name: str) -> str:
        """Reproduce the legacy first-group and anonymous naming scheme."""
        group = block.groups[0] if block.groups else None
        if group is None or group == "default":
            return f"{name}[{block.block_ordinal}]"
        return group

    @staticmethod
    def _apply_block_options(
        test: doctest.DocTest,
        block: doctest_core.ParsedBlock,
    ) -> None:
        """Merge directive policy into each stock example's inline options."""
        block_options = dict(block.options)
        if block.pyversion is not None:
            version = ".".join(str(value) for value in sys.version_info[:3])
            try:
                if not is_allowed_version(version, block.pyversion):
                    block_options[doctest.SKIP] = True
            except InvalidSpecifier:
                logger.warning(
                    "invalid pyversion option",
                    extra={"doctest_source_file": test.filename},
                )
        for example in test.examples:
            options = block_options.copy()
            options.update(example.options)
            example.options = options

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


def _direct_plan(
    plan: doctest_core.GroupPlan,
    *,
    filename: str,
    parser: doctest.DocTestParser,
) -> doctest_core.GroupPlan:
    """Adapt a typed plan to the compatibility facade's names and parser."""
    blocks: list[doctest_core.ProjectedBlock] = []
    for block in plan.blocks:
        block_name = (
            plan.group
            if plan.group != "default"
            else f"{filename}[{block.block_ordinal}]"
        )
        examples = block.examples
        if block.profile_name == "prompt":
            parsed_test = parser.get_doctest(
                block.docstring,
                {},
                block_name,
                block.filename,
                0,
            )
            examples = tuple(
                doctest_core.ExampleRecipe(
                    source=example.source,
                    want=example.want,
                    exc_msg=example.exc_msg,
                    lineno=example.lineno,
                    indent=example.indent,
                    options=types.MappingProxyType(dict(example.options)),
                )
                for example in parsed_test.examples
            )
        blocks.append(block._replace(name=block_name, examples=examples))
    return plan._replace(blocks=tuple(blocks))


def _report_failure(
    runner: doctest.DocTestRunner,
    failure: doctest.DocTestFailure | doctest.UnexpectedException,
) -> None:
    """Render a core failure through the stock direct runner hooks."""
    if isinstance(failure, doctest.DocTestFailure):
        runner.report_failure(
            sys.stdout.write,
            failure.test,
            failure.example,
            failure.got,
        )
        return
    runner.report_unexpected_exception(
        sys.stdout.write,
        failure.test,
        failure.example,
        failure.exc_info,
    )


def _record_statistics(
    runner: doctest.DocTestRunner,
    *,
    name: str,
    failures: int,
    attempted: int,
    skipped: int,
) -> None:
    """Populate CPython's version-specific summary bookkeeping."""
    runner.failures += failures
    runner.tries += attempted
    stats = getattr(runner, "_stats", None)
    if isinstance(stats, dict):
        typed_stats = t.cast(dict[str, tuple[int, int, int]], stats)
        old_failures, old_attempted, old_skipped = typed_stats.get(
            name,
            (0, 0, 0),
        )
        typed_stats[name] = (
            old_failures + failures,
            old_attempted + attempted,
            old_skipped + skipped,
        )
        runner.skips += skipped  # type: ignore[attr-defined]
        return
    name_to_counts = t.cast(
        dict[str, tuple[int, int]],
        runner.__dict__["_name2ft"],
    )
    old_failures, old_attempted = name_to_counts.get(name, (0, 0))
    name_to_counts[name] = (
        old_failures + failures,
        old_attempted + attempted,
    )


def _consume_result(
    runner: doctest.DocTestRunner,
    result: doctest_core.GroupResult,
) -> None:
    """Project one core group result onto the direct doctest runner."""
    for block_result in result.blocks:
        failures = 0
        attempted = 0
        skipped = 0
        if isinstance(block_result, doctest_core.Failed):
            failures = block_result.counts.failed
            attempted = block_result.counts.attempted
            skipped = block_result.counts.skipped
            for failure in block_result.failures:
                _report_failure(runner, failure)
        elif block_result.block.phase is doctest_core.Phase.TEST and isinstance(
            block_result, (doctest_core.Passed, doctest_core.Skipped)
        ):
            attempted = block_result.counts.attempted
            skipped = block_result.counts.skipped
        _record_statistics(
            runner,
            name=block_result.block.name,
            failures=failures,
            attempted=attempted,
            skipped=skipped,
        )
    if result.primary is not None:
        raise result.primary


class TestDocutilsPackageRelativeError(Exception):
    """Raise when doctest_docutils is called for package not relative to module."""

    __test__ = False

    def __init__(self) -> None:
        super().__init__(
            "Package may only be specified for module-relative paths.",
        )


def testdocutils(
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
    text, source_filename = doctest._load_testfile(  # type: ignore
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

    runner: doctest.DebugRunner | doctest.DocTestRunner

    if raise_on_error:
        runner = doctest.DebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = doctest.DocTestRunner(verbose=verbose, optionflags=optionflags)

    source_path = pathlib.Path(source_filename)
    if source_path.suffix not in {".md", ".rst", ".txt"}:
        source_path = source_path.with_suffix(".rst")
    registry = doctest_core.build_registry()
    parsed = doctest_core.parse_document(
        text,
        source_path,
        registry=registry,
    )
    plans = doctest_core.project(
        parsed,
        document_name=name,
        registry=registry,
        seed=globs,
    )
    settings = doctest_core.RunSettings(
        optionflags=optionflags,
        continue_on_failure=(
            not raise_on_error and not bool(optionflags & doctest.FAIL_FAST)
        ),
    )
    for plan in plans:
        direct_plan = _direct_plan(plan, filename=filename, parser=parser)
        live_globs: dict[str, t.Any] = {}
        doctest_core.reset_globs(direct_plan, live_globs)
        result = doctest_core.run_group(
            direct_plan,
            live_globs,
            settings=settings,
            registry=registry,
        )
        _consume_result(runner, result)

    if report:
        runner.summarize()

    if master is None:
        master = runner
    else:
        master.merge(runner)

    if hasattr(runner, "skips"):
        constructor = t.cast(t.Any, doctest.TestResults)
        return t.cast(
            doctest.TestResults,
            constructor(
                runner.failures,
                runner.tries,
                skipped=runner.skips,
            ),
        )
    return doctest.TestResults(runner.failures, runner.tries)


testdocutils.__test__ = False  # type: ignore[attr-defined]


def _test() -> int:
    """Execute doctest module via CLI."""
    import argparse

    p = argparse.ArgumentParser(description="doctest runner")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="list tested groups in the final summary",
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
            failures, _ = testdocutils(  # type: ignore[misc,unused-ignore]
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
