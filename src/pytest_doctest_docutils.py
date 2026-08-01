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
import pathlib
import sys
import typing as t

import _pytest
import pytest
from _pytest import outcomes
from _pytest.outcomes import OutcomeException

from doctest_docutils import (
    _HIDE_FLAG,
    DEFAULT_NAMESPACE_ITEMS,
    DEFAULT_NAMESPACE_SCOPE,
    NAMESPACE_ITEMS,
    NAMESPACE_SCOPES,
    DocutilsDocTestFinder,
    NamespaceItems,
    NamespaceItemsError,
    NamespaceScope,
    NamespaceScopeError,
    _ensure_directives_registered,
    _parse_namespace_items,
    _parse_namespace_scope,
)

if t.TYPE_CHECKING:
    import types
    from collections.abc import Iterable
    from doctest import _Out

    from _pytest.config.argparsing import Parser
    from _pytest.doctest import DoctestItem


logger = logging.getLogger(__name__)

# Parse pytest version for version-specific features
PYTEST_VERSION = tuple(int(x) for x in pytest.__version__.split(".")[:2])

# Lazy definition of runner class
RUNNER_CLASS = None

#: Namespace scope resolved once at configure time, read back during collection.
_NAMESPACE_SCOPE_KEY = pytest.StashKey[NamespaceScope]()

#: Namespace layout resolved once at configure time, read back during collection.
_NAMESPACE_ITEMS_KEY = pytest.StashKey[NamespaceItems]()

_NAMESPACE_HELP = (
    "namespace the doctest blocks of one .rst/.md file run in when they name"
    " no group: block (default, one each) or document (one for the page);"
    " blocks naming a group always share that group's namespace"
)

_ITEMS_HELP = (
    "what a namespace collects as: merged (default, one item holding every"
    " block of it) or per-block (one item per block, keeping their node ids"
    " and sharing the namespace between them)"
)

#: The ``--dist`` values that keep every item of one file on one worker, which
#: is what a shared namespace needs: a globals mapping is a Python object, so
#: it does not cross processes. Named as an allowlist rather than a list of
#: splitting schedulers so that a scheduler pytest-xdist adds later is refused
#: until it has been checked, instead of silently splitting a namespace.
#: ``load`` and ``worksteal`` hand a file's items to whichever worker is free;
#: ``-n`` without ``--dist`` resolves to ``load``.
_WHOLE_NAMESPACE_SCHEDULERS = frozenset(
    {"no", "each", "loadfile", "loadgroup", "loadscope"},
)


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
    group.addoption(
        "--doctest-docutils-namespace-scope",
        action="store",
        choices=NAMESPACE_SCOPES,
        default=None,
        help=(
            f"{_NAMESPACE_HELP}; overrides the doctest_docutils_namespace_scope"
            " ini option"
        ),
        dest="doctest_docutils_namespace_scope",
    )
    parser.addini(
        "doctest_docutils_namespace_scope",
        _NAMESPACE_HELP,
        default=DEFAULT_NAMESPACE_SCOPE,
    )
    group.addoption(
        "--doctest-docutils-namespace-items",
        action="store",
        choices=NAMESPACE_ITEMS,
        default=None,
        help=(
            f"{_ITEMS_HELP}; overrides the doctest_docutils_namespace_items ini option"
        ),
        dest="doctest_docutils_namespace_items",
    )
    parser.addini(
        "doctest_docutils_namespace_items",
        _ITEMS_HELP,
        default=DEFAULT_NAMESPACE_ITEMS,
    )


def _resolve_namespace_scope(
    cli_value: str | None,
    ini_value: str | None,
) -> NamespaceScope:
    """Resolve the namespace scope: command line first, then ini, then default.

    Parameters
    ----------
    cli_value : str | None
        Value of ``--doctest-docutils-namespace-scope``, `None` when unset.
    ini_value : str | None
        Value of the ``doctest_docutils_namespace_scope`` ini option.

    Returns
    -------
    doctest_docutils.NamespaceScope
        Scope to build the finder with.

    Raises
    ------
    pytest.UsageError
        If either value names a scope that does not exist.

    Examples
    --------
    >>> _resolve_namespace_scope(None, None)
    'block'

    >>> _resolve_namespace_scope(None, "document")
    'document'

    One run can narrow a project that shares each page, without editing the
    configuration everyone else reads:

    >>> _resolve_namespace_scope("block", "document")
    'block'

    A name that no scope answers to stops the session once, rather than
    failing every file it collects, and says where the name was written —
    argparse already names the flag, so only the ini file needs saying:

    >>> try:
    ...     _resolve_namespace_scope(None, "per-file")
    ... except pytest.UsageError as exc:
    ...     print(exc)
    Unknown namespace scope: 'per-file'. Expected one of: block, document
    Set by the doctest_docutils_namespace_scope ini option.
    """
    value = cli_value or ini_value or DEFAULT_NAMESPACE_SCOPE
    try:
        return _parse_namespace_scope(value)
    except NamespaceScopeError as exc:
        message = str(exc)
        if value == ini_value:
            message += "\nSet by the doctest_docutils_namespace_scope ini option."
        raise pytest.UsageError(message) from exc


def _resolve_namespace_items(
    cli_value: str | None,
    ini_value: str | None,
) -> NamespaceItems:
    """Resolve the namespace layout: command line first, then ini, then default.

    Parameters
    ----------
    cli_value : str | None
        Value of ``--doctest-docutils-namespace-items``, `None` when unset.
    ini_value : str | None
        Value of the ``doctest_docutils_namespace_items`` ini option.

    Returns
    -------
    doctest_docutils.NamespaceItems
        Layout to build the finder with.

    Raises
    ------
    pytest.UsageError
        If either value names a layout that does not exist.

    Examples
    --------
    >>> _resolve_namespace_items(None, None)
    'merged'

    >>> _resolve_namespace_items(None, "per-block")
    'per-block'

    One run can merge a project that keeps its blocks apart, without editing
    the configuration everyone else reads:

    >>> _resolve_namespace_items("merged", "per-block")
    'merged'

    A name that no layout answers to stops the session once, and says where
    the name was written:

    >>> try:
    ...     _resolve_namespace_items(None, "one-each")
    ... except pytest.UsageError as exc:
    ...     print(exc)
    Unknown namespace items: 'one-each'. Expected one of: merged, per-block
    Set by the doctest_docutils_namespace_items ini option.
    """
    value = cli_value or ini_value or DEFAULT_NAMESPACE_ITEMS
    try:
        return _parse_namespace_items(value)
    except NamespaceItemsError as exc:
        message = str(exc)
        if value == ini_value:
            message += "\nSet by the doctest_docutils_namespace_items ini option."
        raise pytest.UsageError(message) from exc


def pytest_configure(config: pytest.Config) -> None:
    """Disable pytest.doctest to prevent running tests twice.

    Todo: Find a way to make these plugins cooperate without collecting twice.
    """
    # Resolved once, so a misspelled scope stops the session here instead of
    # erroring on every file collected.
    config.stash[_NAMESPACE_SCOPE_KEY] = _resolve_namespace_scope(
        config.getoption("doctest_docutils_namespace_scope", None),
        config.getini("doctest_docutils_namespace_scope"),
    )
    config.stash[_NAMESPACE_ITEMS_KEY] = _resolve_namespace_items(
        config.getoption("doctest_docutils_namespace_items", None),
        config.getini("doctest_docutils_namespace_items"),
    )
    # Registered whether or not anything will carry it, so that a project
    # running --strict-markers passes without opting into the layout that
    # emits the marker. Only when pytest-xdist is absent, though: xdist
    # registers the same name itself, and registering it twice lists it twice
    # in ``pytest --markers`` for every project, opted in or not.
    if not config.pluginmanager.hasplugin("xdist"):
        config.addinivalue_line(
            "markers",
            "xdist_group(name): keep a namespace's blocks on one pytest-xdist"
            " worker under --dist loadgroup",
        )
    if config.pluginmanager.has_plugin("doctest"):
        config.pluginmanager.set_blocked("doctest")


def pytest_sessionstart(session: pytest.Session) -> None:
    """Stop a run whose scheduler would split a shared namespace across workers.

    Blocks laid out ``per-block`` can hold one globals mapping between them —
    any page declaring a group does, whatever the scope — and a mapping does
    not cross processes. ``--dist load`` and ``--dist worksteal`` hand a file's
    items to whichever worker is free, so half a namespace can land on a worker
    that never ran the block binding the names it reads, which reports as a
    ``NameError`` in the page rather than as the configuration problem it is.

    Refused only for a run that would really distribute, matching xdist's own
    condition: it declines to distribute under ``--collect-only``, and with
    fewer than two workers there is nothing to split a namespace between.

    The scheduler is only knowable on the controller: a worker is told
    ``dist`` is ``no`` whatever the controller was given, which is why the
    check is gated on ``is_xdist_controller``. The controller never collects,
    so which pages a run holds cannot be known here — selecting ``per-block``
    is what the refusal reads as the opt-in.

    Parameters
    ----------
    session : pytest.Session
        Session about to run, which carries the resolved ``--dist`` value.

    Raises
    ------
    pytest.UsageError
        If the namespace layout and the scheduler cannot both hold.
    """
    config = session.config
    if config.stash[_NAMESPACE_ITEMS_KEY] != "per-block":
        return
    if not config.pluginmanager.hasplugin("xdist"):
        return
    from xdist import (  # type: ignore[import-untyped,unused-ignore]
        is_xdist_controller,
    )

    if not is_xdist_controller(session):
        return
    if config.getoption("collectonly", False):
        return
    if len(config.getoption("tx", None) or []) < 2:
        return
    scheduler = config.getoption("dist", "no")
    if scheduler in _WHOLE_NAMESPACE_SCHEDULERS:
        return
    message = (
        "doctest_docutils_namespace_items = per-block can hand a namespace's"
        " blocks one globals mapping between them — a page declaring a group"
        " does, whatever the scope — and a mapping cannot cross processes."
        f" --dist {scheduler} hands a file's items to whichever worker is"
        " free, so it can send them to different workers. Run with --dist"
        " loadgroup or --dist loadfile, or set"
        " doctest_docutils_namespace_items = merged. -n without --dist"
        " selects --dist load."
    )
    raise pytest.UsageError(message)


def pytest_report_header(config: pytest.Config) -> str | None:
    """Say how namespaces are laid out, when they are not laid out as usual.

    A run that changed nothing reports nothing, so the header of an
    unconfigured project reads as it always has.

    Parameters
    ----------
    config : pytest.Config
        Configuration holding the resolved settings.

    Returns
    -------
    str or None
        One line naming the layout and the scope, or `None` under the default
        layout.
    """
    items = config.stash[_NAMESPACE_ITEMS_KEY]
    if items == DEFAULT_NAMESPACE_ITEMS:
        return None
    scope = config.stash[_NAMESPACE_SCOPE_KEY]
    return f"doctest-docutils: namespace items: {items}, namespace scope: {scope}"


def _unblock_doctest(config: pytest.Config) -> bool:
    """Unblock doctest plugin (pytest 8.1+ only).

    Re-enables the built-in doctest plugin after it was blocked by
    pytest_configure. Uses the public unblock() API introduced in pytest 8.1.0.

    Parameters
    ----------
    config : pytest.Config
        The pytest configuration object

    Returns
    -------
    bool
        True if unblocked successfully, False if API not available
    """
    pm = config.pluginmanager
    if PYTEST_VERSION >= (8, 1) and hasattr(pm, "unblock"):
        return pm.unblock("doctest")
    return False


def pytest_unconfigure() -> None:
    """Unconfigure hook for pytest-doctest-docutils."""
    global RUNNER_CLASS

    RUNNER_CLASS = None


def pytest_ignore_collect(collection_path: pathlib.Path) -> bool | None:
    """Skip Sphinx ``_build/`` output during collection.

    pytest's default ``norecursedirs`` excludes ``build`` but not ``_build``,
    so Sphinx output (which mirrors sources, broken relative includes and all)
    would otherwise be collected and abort the session.

    >>> import pathlib
    >>> pytest_ignore_collect(pathlib.Path("docs/_build/html/history.md"))
    True
    >>> pytest_ignore_collect(pathlib.Path("docs/history.md")) is None
    True
    """
    if "_build" in collection_path.parts:
        return True
    return None


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
            share_globs: bool = False,
        ) -> None:
            super().__init__(checker=checker, verbose=verbose, optionflags=optionflags)
            self.continue_on_failure = continue_on_failure
            self.share_globs = share_globs

        def run(
            self,
            test: doctest.DocTest,
            compileflags: int | None = None,
            out: _Out | None = None,
            clear_globs: bool = True,
        ) -> doctest.TestResults:
            """Run one test, keeping its globals when its namespace shares them.

            ``clear_globs`` empties ``test.globs`` once the test is done, which
            is what stops one item's bindings reaching the next. A namespace
            laid out per block wants exactly that reach: its items hold one
            mapping between them, so the block below reads what this one bound.
            """
            return super().run(
                test,
                compileflags,
                out,
                clear_globs and not self.share_globs,
            )

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


def _get_hide_flag() -> int:
    """Return the HIDE flag, registered by importing :mod:`doctest_docutils`.

    ``HIDE`` is a no-op for execution: the output checker never consults it.
    It marks a doctest example that documentation tooling should drop from the
    rendered output while still running it as a test.
    """
    return _HIDE_FLAG


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
        "HIDE": _get_hide_flag(),
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
    share_globs: bool = False,
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
        share_globs=share_globs,
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


def _wholly_skipped_reason(test: doctest.DocTest) -> str | None:
    r"""Return why a test is skipped outright, or `None` when it runs something.

    Parameters
    ----------
    test : doctest.DocTest
        Collected test, one namespace or one block lifted out of it.

    Returns
    -------
    str or None
        Reason naming the page and the first line skipped, or `None`.

    Examples
    --------
    >>> import doctest
    >>> parser = doctest.DocTestParser()
    >>> running = parser.get_doctest(">>> 2 + 2\n4\n", {}, "page", "page.rst", 3)
    >>> _wholly_skipped_reason(running) is None
    True

    >>> gated = parser.get_doctest(
    ...     ">>> 2 + 2  # doctest: +SKIP\n4\n", {}, "page", "page.rst", 3
    ... )
    >>> _wholly_skipped_reason(gated)
    'page.rst:4: every example skipped'

    The page is named, not the path it resolves, which pytest prints beside the
    reason already:

    >>> nested = parser.get_doctest(
    ...     ">>> 2 + 2  # doctest: +SKIP\n4\n", {}, "page", "docs/a/page.rst", 3
    ... )
    >>> _wholly_skipped_reason(nested)
    'page.rst:4: every example skipped'

    A block holding no example at all skips nothing, which is not the same
    answer as every example being skipped — ``all([])`` is `True`:

    >>> empty = parser.get_doctest("prose only\n", {}, "page", "page.rst", 3)
    >>> _wholly_skipped_reason(empty) is None
    True
    """
    if not test.examples:
        return None
    if not all(example.options.get(doctest.SKIP, False) for example in test.examples):
        return None
    line = (test.lineno or 0) + test.examples[0].lineno + 1
    page = pathlib.Path(test.filename or "").name
    return f"{page}:{line}: every example skipped"


class DocTestDocutilsFile(pytest.Module):
    """Pytest module for doctest_docutils."""

    obj = None  # Fix pytest-asyncio issue. #46, pytest-asyncio#872

    def collect(self) -> Iterable[DoctestItem]:
        """Collect tests for pytest module."""
        _ensure_directives_registered()

        encoding = self.config.getini("doctest_encoding")
        text = self.path.read_text(encoding)

        namespace_items = self.config.stash[_NAMESPACE_ITEMS_KEY]
        per_block = namespace_items == "per-block"

        # Uses internal doctest module parsing mechanism.
        finder = DocutilsDocTestFinder(
            namespace_scope=self.config.stash[_NAMESPACE_SCOPE_KEY],
            namespace_items=namespace_items,
        )

        # While doctests in .rst/.md files don't support fixtures directly,
        # we still need to pick up autouse fixtures.
        # Backported from pytest commit 9cd14b4ff (2024-02-06).
        # https://github.com/pytest-dev/pytest/commit/9cd14b4ff
        self.session._fixturemanager.parsefactories(self)

        optionflags = get_optionflags(self.config)

        runner = _get_runner(
            verbose=False,
            optionflags=optionflags,
            checker=_pytest.doctest._get_checker(),
            continue_on_failure=_pytest.doctest._get_continue_on_failure(self.config),
            share_globs=per_block,
        )
        from _pytest.doctest import DoctestItem

        for collected in finder._collect(
            text,
            str(self.path),
        ):
            test = collected.test
            if test.examples:  # skip empty doctests
                item = DoctestItem.from_parent(
                    self,  # type: ignore
                    name=test.name,
                    runner=runner,
                    dtest=test,
                )
                if per_block:
                    # pytest-xdist reads this on the worker and suffixes the
                    # node id with the group, so --dist loadgroup keeps a
                    # namespace whole. It cannot choose the scheduler, which is
                    # why an unusable one is refused at session start instead.
                    item.add_marker(
                        pytest.mark.xdist_group(
                            f"{self.nodeid}::{collected.namespace}",
                        ),
                    )
                reason = _wholly_skipped_reason(test)
                if reason is not None:
                    # Marked rather than left to _check_all_skipped, which only
                    # fires once the item is running: by then its fixtures have
                    # set up for a test that executes nothing. A marker is read
                    # before setup, and it carries a reason naming the block.
                    item.add_marker(pytest.mark.skip(reason=reason))
                yield item
