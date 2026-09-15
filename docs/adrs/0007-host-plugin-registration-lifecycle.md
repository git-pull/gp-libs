(adr-0007-host-plugin-registration-lifecycle)=

# ADR 0007: Host plugin registration lifecycle

Status: Draft
Date: 2026-08-02

## Context

{doc}`0001-typed-vanilla-doctest-core` makes block kinds, document parsers,
execution profiles and output checkers extensible. The core needs one typed
contribution contract, but its hosts discover contributors at different times:
direct callers already have an explicit iterable, pytest loads installed plugins
and conftests in stages, and Sphinx loads extensions before it reads doctrees.

Treating settings and registrations as one object obscures that difference.
Settings are normalized user input. Registrations are discovered capabilities,
and xdist may discover them in more than one process. The mutable construction
mechanism must not leak into parsing or execution.

## Decision

The public boundary consists of `Contributor`, `Registrar`, immutable registration
records and `RegistrySnapshot`. A private builder is the only mutable object. It
accepts contributions, validates them and produces a snapshot; every parser,
projector and runner receives that snapshot explicitly.

```python
T = t.TypeVar("T")


class Provider(t.NamedTuple):
    name: str
    version: str | None


class Registration(t.NamedTuple, t.Generic[T]):
    name: str
    value: T
    provider: Provider


class Contributor(t.Protocol):
    provider: Provider

    def contribute(self, registrar: Registrar) -> None: ...


class Registrar(t.Protocol):
    def add_block_kind(
        self, name: str, kind: BlockKind, *, replace: bool = False
    ) -> None: ...

    def add_document_parser(
        self, name: str, parser: DocumentParser, *, replace: bool = False
    ) -> None: ...

    def add_execution_profile(
        self, name: str, profile: ExecutionProfile, *, replace: bool = False
    ) -> None: ...

    def add_output_checker(
        self, name: str, factory: CheckerFactory, *, replace: bool = False
    ) -> None: ...


class RegistrySnapshot(t.NamedTuple):
    block_kinds: t.Mapping[str, Registration[BlockKind]]
    document_parsers: t.Mapping[str, Registration[DocumentParser]]
    execution_profiles: t.Mapping[str, Registration[ExecutionProfile]]
    output_checkers: t.Mapping[str, Registration[CheckerFactory]]


def build_registry(
    contributors: t.Iterable[Contributor] = (),
) -> RegistrySnapshot: ...
```

The snapshot fields are read-only `MappingProxyType` views over private copies,
not mutable dictionaries typed as `Mapping`. The builder is discarded after
`freeze()`. While applying each `Contributor`, the builder gives it a registrar
bound to that contributor's `Provider`; registrations cannot claim a different
origin. A contributor retaining that registrar cannot retain a mutation path:
every method raises `RegistryClosedError` after the snapshot is made.

### Names, collisions and order

Registration names are case-sensitive ASCII identifiers matching
`[a-z][a-z0-9_.-]*`. The same name may exist in different categories. Within one
category a duplicate is an error naming the category, incumbent provider and
challenger provider unless the challenger passes `replace=True`. Replacement
retains the incumbent's insertion position, so an explicit override cannot
silently reorder parser or profile selection.

Built-ins register first. Contributor order is then the order supplied by the
host, and calls within a contributor retain program order. The snapshot preserves
that order. Any selection rule that needs precedence uses this declared sequence;
it never sorts by an implementation object's representation or module path.

For document parsers, overlapping suffix claims are also collisions. They are
accepted only when the challenger uses the incumbent parser's name and passes
`replace=True`; two differently named parsers cannot both win `.md` by incidental
plugin load order.

## Host adapters

### Direct API

Direct callers pass contributors to `build_registry()`. The function registers
built-ins, applies the iterable once, freezes and returns `RegistrySnapshot`.
There is no entry-point scan or process-global default in the core API.

### pytest

The pytest adapter publishes its hookspec in `pytest_addhooks`:

```python
class DoctestCoreHooks:
    @pytest.hookspec
    def pytest_doctest_core_contributors(
        self,
    ) -> Contributor | t.Iterable[Contributor] | None:
        """Return doctest-core contributors before collection."""
```

Its `pytest_configure(trylast=True)` implementation invokes the hook, flattens
its non-`None` results in pluggy's hook-call order, builds the registry and stores
the snapshot on pytest's stash. Installed plugins and initial conftests are
already registered at that point. The snapshot is therefore ready before
`pytest_sessionstart`, when xdist starts controller nodes, and before collection.

Nested conftests load during collection and are outside this lifecycle. A
`pytest_plugin_registered` guard detects a late plugin implementing the hookspec
and raises `pytest.UsageError` naming that plugin and the closed registration
phase. Fixtures and unrelated hooks in nested conftests remain valid.

### Sphinx

The Sphinx adapter exposes
`add_doctest_core_contributor(app, contributor)`. Extensions call it from their
`setup(app)` function. At `config-inited`, after extension setup and before any
document is read, the adapter emits a `doctest-core-contributors` event, appends
the `Contributor` objects returned by its listeners to the queued contributors,
builds the registry and freezes the snapshot on the application.

The adapter function is the order-independent path. An extension that connects
directly to the custom event must list the doctest-core extension before itself,
because Sphinx cannot connect a listener to an event that has not been declared.
Calling the adapter after `config-inited` raises `RegistryClosedError` with the
extension name.

This lifecycle makes the extractor usable on Sphinx-resolved doctrees. It does
not add a builder or claim parity with `sphinx-build -b doctest` execution.

## xdist consistency

The controller sends a JSON-safe manifest through `workerinput` from
`pytest_configure_node`. Each worker builds its own snapshot during
`pytest_configure` and compares before collection. The manifest has a schema
version and contains:

- a JSON-safe projection of normalized `SessionSettings`
- every registry category, name, provider and provider version in declared order
- `doctest.OPTIONFLAGS_BY_NAME`, sorted by flag name

A mismatch aborts the session with the controller and worker manifests. This is
an extension-set consistency check, not proof that two workers are semantically
identical. Equal provider names and versions do not prove equal source code, and
the manifest does not hash included documents, directive implementations or MyST
plugins.

Version 1 therefore supports homogeneous worker environments. Equal source
closure and equal installed provider code are preconditions, while xdist's own
identical-collection check remains authoritative for node ids. Stronger support
for deliberately heterogeneous SSH or socket workers would require content or
environment attestation and is deferred.

## Consequences

- Core extension authors implement one `Contributor` regardless of host.
- Settings remain serializable inputs; discovered objects remain in the registry.
- Parse and execution code cannot mutate capabilities after collection starts.
- pytest and Sphinx own timing and diagnostics in their native idioms without
  leaking their lifecycle types into the core.
- Replacement is possible but visible, attributed and deterministic.
- Supporting heterogeneous xdist workers is explicitly outside the first
  contract rather than implied by a weak manifest.

## Open

- Whether a later release should add opt-in entry-point discovery to the direct
  adapter. The core function remains explicit either way.
- Whether provider code hashes are useful enough to justify the packaging and
  editable-install edge cases they introduce.
