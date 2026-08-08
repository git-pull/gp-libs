"""Pytest host adapter for the typed doctest core."""

from __future__ import annotations

import bdb
import collections.abc
import doctest
import pathlib
import traceback
import typing as t
import weakref

import pytest

import _pytest_doctest_compat as compat
from doctest_core import (
    Contributor,
    Errored,
    Failed,
    GroupPlan,
    GroupResult,
    Phase,
    ProjectionSettings,
    Provider,
    Registrar,
    RegistrySnapshot,
    RunSettings,
    Skipped,
    build_registry,
    parse_document,
    project,
    reset_globs,
    run_group,
)
from doctest_core.markup import ensure_directives_registered

if t.TYPE_CHECKING:
    from _pytest._code import ExceptionInfo
    from _pytest._code.code import TerminalRepr
    from _pytest.config import PytestPluginManager
    from _pytest.config.argparsing import Parser


PYTEST_VERSION = tuple(int(part) for part in pytest.__version__.split(".")[:2])
_REGISTRY_KEY: pytest.StashKey[RegistrySnapshot] = pytest.StashKey()
_FROZEN_PLUGIN_MANAGERS: weakref.WeakSet[t.Any] = weakref.WeakSet()


class DoctestCoreHooks:
    """Hooks published by the doctest-core pytest adapter."""

    @pytest.hookspec
    def pytest_doctest_core_contributors(
        self,
    ) -> Contributor | collections.abc.Iterable[Contributor] | None:
        """Return host-neutral contributors before collection."""


class _PytestContributor:
    """Use pytest's checker for the core's default checker registration."""

    provider = Provider(name="pytest", version=pytest.__version__)

    def contribute(self, registrar: Registrar) -> None:
        """Replace the stdlib checker with pytest's compatible extension."""
        registrar.add_output_checker(
            "stdlib",
            compat.get_checker,
            replace=True,
        )


class _PytestExceptionPolicy:
    """Classify pytest outcomes and process aborts for the core runtime."""

    def should_propagate(self, error: BaseException) -> bool:
        """Return whether pytest, rather than doctest, owns ``error``."""
        outcome_types = (
            pytest.skip.Exception,
            pytest.xfail.Exception,
            pytest.fail.Exception,
            pytest.exit.Exception,
        )
        return isinstance(
            error,
            (*outcome_types, KeyboardInterrupt, SystemExit, bdb.BdbQuit),
        )

    def is_abort(self, error: BaseException) -> bool:
        """Return whether ``error`` must abort despite prior block outcomes.

        >>> _PytestExceptionPolicy().is_abort(KeyboardInterrupt())
        True
        >>> _PytestExceptionPolicy().is_abort(ValueError())
        False
        """
        return isinstance(
            error,
            (pytest.exit.Exception, KeyboardInterrupt, SystemExit, bdb.BdbQuit),
        )


def pytest_addhooks(pluginmanager: PytestPluginManager) -> None:
    """Publish the contributor hook before pytest loads initial conftests."""
    pluginmanager.add_hookspecs(DoctestCoreHooks)


def pytest_plugin_registered(
    plugin: object,
    manager: PytestPluginManager,
) -> None:
    """Reject contributor hooks registered after the host snapshot freezes.

    >>> callable(pytest_plugin_registered)
    True
    """
    if manager not in _FROZEN_PLUGIN_MANAGERS:
        return
    contributor_hook = getattr(plugin, "pytest_doctest_core_contributors", None)
    if callable(contributor_hook):
        plugin_name = manager.get_name(plugin) or type(plugin).__name__
        message = (
            f"pytest plugin {plugin_name!r} registered a doctest-core contributor "
            "after the contribution phase closed"
        )
        raise pytest.UsageError(message)


def pytest_addoption(parser: Parser) -> None:
    """Add doctest-docutils host options."""
    group = parser.getgroup("collect")
    group.addoption(
        "--doctest-docutils-modules",
        action="store_true",
        default=False,
        help="run doctests in Python modules through pytest's doctest plugin",
        dest="doctestmodules",
    )
    group.addoption(
        "--no-doctest-docutils-modules",
        action="store_false",
        help="disable doctests in Python modules",
        dest="doctestmodules",
    )
    parser.addini(
        "doctest_docutils_ungrouped",
        "sharing policy for bare documentation blocks: block or default",
        default="block",
    )


def _flatten_contributors(results: t.Iterable[object]) -> list[Contributor]:
    """Flatten pluggy's per-implementation return values in hook order."""
    contributors: list[Contributor] = []
    for result in results:
        if result is None:
            continue
        if hasattr(result, "contribute") and hasattr(result, "provider"):
            contributors.append(t.cast(Contributor, result))
            continue
        if isinstance(result, collections.abc.Iterable):
            contributors.extend(t.cast(collections.abc.Iterable[Contributor], result))
    return contributors


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Freeze host contributions without unregistering pytest's doctest plugin."""
    doctest.register_optionflag("HIDE")
    raw_hook = t.cast(t.Any, config.hook).pytest_doctest_core_contributors()
    contributors = [_PytestContributor(), *_flatten_contributors(raw_hook)]
    config.stash[_REGISTRY_KEY] = build_registry(contributors)
    _FROZEN_PLUGIN_MANAGERS.add(config.pluginmanager)
    value = config.getini("doctest_docutils_ungrouped")
    if value not in {"block", "default"}:
        message = "doctest_docutils_ungrouped must be 'block' or 'default'"
        raise pytest.UsageError(message)


def pytest_ignore_collect(collection_path: pathlib.Path) -> bool | None:
    """Skip generated Sphinx ``_build`` trees.

    >>> pytest_ignore_collect(pathlib.Path("docs/_build/html/page.md"))
    True
    >>> pytest_ignore_collect(pathlib.Path("docs/page.md")) is None
    True
    """
    if "_build" in collection_path.parts:
        return True
    return None


def _is_doctest(
    config: pytest.Config,
    path: pathlib.Path,
    parent: pytest.Collector,
) -> bool:
    """Return whether this adapter claims a documentation path."""
    registry = config.stash.get(_REGISTRY_KEY, None)
    supported_suffixes = (
        {
            suffix
            for registration in registry.document_parsers.values()
            for suffix in registration.value.suffixes
        }
        if registry is not None
        else {".rst", ".md"}
    )
    if path.suffix not in supported_suffixes:
        return False
    if parent.session.isinitpath(path):
        return True
    patterns = config.getoption("doctestglob", default=None) or ["*.rst", "*.md"]
    return any(path.match(pattern) for pattern in patterns)


@pytest.hookimpl(hookwrapper=True, tryfirst=True, specname="pytest_collect_file")
def pytest_collect_file_filter(
    file_path: pathlib.Path,
    parent: pytest.Collector,
) -> t.Generator[None, object, None]:
    """Remove pytest's duplicate textfile collector before it parses the file."""
    outcome = yield
    if not _is_doctest(parent.config, file_path, parent):
        return
    hook_result = t.cast(t.Any, outcome).get_result()
    filtered = [
        collector
        for collector in hook_result
        if not isinstance(collector, compat.DoctestTextfile)
    ]
    t.cast(t.Any, outcome).force_result(filtered)


def pytest_collect_file(
    file_path: pathlib.Path,
    parent: pytest.Collector,
) -> DocTestDocutilsFile | pytest.Collector | None:
    """Collect documentation here and delegate Python modules to pytest."""
    config = parent.config
    if file_path.suffix == ".py":
        if config.option.doctestmodules and not config.pluginmanager.has_plugin(
            "doctest",
        ):
            message = (
                f"{file_path}: --doctest-docutils-modules requires pytest's "
                "built-in doctest plugin"
            )
            raise pytest.UsageError(message)
        return None
    if _is_doctest(config, file_path, parent):
        return DocTestDocutilsFile.from_parent(parent, path=file_path)
    return None


def get_optionflags(config: pytest.Config) -> int:
    """Return pytest's resolved doctest option flags."""
    return compat.get_optionflags(config)


class DocutilsItem(pytest.DoctestItem):
    """One pytest item owning one shared-state doctest group."""

    @classmethod
    def from_parent(  # type: ignore[override]
        cls,
        parent: pytest.Collector,
        *,
        name: str,
        runner: doctest.DocTestRunner,
        dtest: doctest.DocTest,
        plan: GroupPlan,
        registry: RegistrySnapshot,
        run_settings: RunSettings,
    ) -> DocutilsItem:
        """Construct through pytest's cooperative item factory."""
        item = super(pytest.DoctestItem, cls).from_parent(
            parent=parent,
            name=name,
            runner=runner,
            dtest=dtest,
            plan=plan,
            registry=registry,
            run_settings=run_settings,
        )
        return item

    def __init__(
        self,
        *,
        plan: GroupPlan,
        registry: RegistrySnapshot,
        run_settings: RunSettings,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self.plan = plan
        self.registry = registry
        self.run_settings = run_settings
        self.group_result: GroupResult | None = None
        self._failure_checkers: dict[int, doctest.OutputChecker] = {}

    def setup(self) -> None:
        """Reset attempt state, then let pytest inject fixtures in place."""
        reset_globs(self.plan, self.dtest.globs)
        super().setup()

    def runtest(self) -> None:
        """Run all block doctests in phase order against the carrier mapping."""
        compat.disable_output_capturing_for_darwin(self)
        result = run_group(
            self.plan,
            self.dtest.globs,
            settings=self.run_settings,
            registry=self.registry,
            exception_policy=_PytestExceptionPolicy(),
        )
        self.group_result = result
        self._failure_checkers = {
            id(failure): block.checker
            for block in result.blocks
            if isinstance(block, Failed)
            for failure in block.failures
        }
        if result.secondary:
            details = "\n\n".join(
                "".join(
                    traceback.format_exception(
                        type(error),
                        error,
                        error.__traceback__,
                    ),
                )
                for error in result.secondary
            )
            self.add_report_section("call", "doctest cleanup", details)
        if result.primary is not None:
            if isinstance(result.primary, bdb.BdbQuit):
                pytest.exit("Quitting debugger")
            cleanup_outcome = any(
                isinstance(block, Errored)
                and block.block.phase is Phase.CLEANUP
                and block.error is result.primary
                for block in result.blocks
            )
            if cleanup_outcome and isinstance(
                result.primary,
                (pytest.skip.Exception, pytest.xfail.Exception),
            ):
                message = (
                    "doctest cleanup raised "
                    f"{type(result.primary).__name__}: {result.primary}"
                )
                raise RuntimeError(message) from result.primary
            raise result.primary

        failures = [
            failure
            for block in result.blocks
            if isinstance(block, Failed)
            for failure in block.failures
        ]
        if failures:
            raise compat.make_multiple_failures(failures)

        test_results = [
            block
            for block in result.blocks
            if block.block.phase is Phase.TEST and not isinstance(block, Errored)
        ]
        if test_results and all(isinstance(block, Skipped) for block in test_results):
            pytest.skip("all examples were skipped")

    def repr_failure(  # type: ignore[override]
        self,
        excinfo: ExceptionInfo[BaseException],
    ) -> str | TerminalRepr:
        """Use comparison-time checkers for contributed output semantics."""
        rendered = compat.repr_failure_with_checkers(
            self,
            excinfo,
            self._failure_checkers,
        )
        if rendered is not None:
            return rendered
        return super().repr_failure(excinfo)


class DocTestDocutilsFile(pytest.Module):
    """Documentation module projecting one item per doctest group."""

    obj = None

    def collect(self) -> collections.abc.Iterable[DocutilsItem]:
        """Parse once, project pure plans, and build synthetic carriers."""
        if not self.config.pluginmanager.has_plugin("doctest"):
            message = (
                f"{self.path}: documentation collection requires pytest's "
                "built-in doctest plugin"
            )
            raise pytest.UsageError(message)
        ensure_directives_registered()
        encoding = self.config.getini("doctest_encoding")
        text = self.path.read_text(encoding=encoding)
        registry = self.config.stash[_REGISTRY_KEY]
        parsed = parse_document(text, self.path, registry=registry)

        ungrouped = t.cast(
            t.Literal["block", "default"],
            self.config.getini("doctest_docutils_ungrouped"),
        )
        plans = project(
            parsed,
            document_name=self.path.name,
            settings=ProjectionSettings(ungrouped=ungrouped),
            registry=registry,
        )
        optionflags = get_optionflags(self.config)
        continue_on_failure = compat.get_continue_on_failure(self.config)
        for plan in plans:
            globs: dict[str, t.Any] = {}
            carrier = doctest.DocTest(
                [],
                globs,
                plan.group,
                str(self.path),
                0,
                "",
            )
            carrier.globs = globs
            runner = doctest.DocTestRunner(
                checker=compat.get_checker(),
                optionflags=optionflags,
            )
            yield DocutilsItem.from_parent(
                self,
                name=plan.group,
                runner=runner,
                dtest=carrier,
                plan=plan,
                registry=registry,
                run_settings=RunSettings(
                    optionflags=optionflags,
                    continue_on_failure=continue_on_failure,
                    checker_name="stdlib",
                ),
            )
