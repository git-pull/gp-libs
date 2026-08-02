# Cross-cutting: extension seams

Five mechanisms appear across these systems. They are not equally good, and the
ranking is not a matter of taste — each has an observed failure mode.

## The five mechanisms

| Mechanism | Where | Failure mode |
|---|---|---|
| **Nominal subclassing** — the *type checker* demands the class, the interpreter does not | stdlib `doctest` (via typeshed), `sphinx.ext.doctest` directives | Typed callers are rejected for objects that work fine at runtime. stdlib performs no `isinstance` check on `parser` or `test_finder`; the pressure comes entirely from `doctest.pyi`. One genuine runtime edge: `DocTestSuite` sorts, and `DocTest.__lt__` returns `NotImplemented` for a non-`DocTest`, so a custom finder must return real `DocTest`s |
| **Callable aliases** — `Evaluator = Callable[[Example], str \| None]` | Sybil | Types nothing. You cannot express "this lexer emits `source` and `arguments`", so a mismatched pairing raises `KeyError` at run time. Sybil's own source comments say the payload "could likely be a `TypedDict`" |
| **Named registry** — a module dict plus a `register_*` function | `doctest.register_optionflag`, docutils directives, xdoctest's two facades | Process-global mutable state. Order-dependent, unscoped, and silently overwritable |
| **`Protocol`** — structural typing | xdoctest's `StdlibExampleLike` | None inherent; but a `Protocol` alone does not satisfy a nominal consumer |
| **Hookspec** — the host's own plugin protocol | pytest, pytest-asyncio's `PytestAsyncioSpecs` | Requires a host with a plugin system; not available to a library core |

## Why `register_optionflag` works and the docutils registry does not

Both are process-global mutable dicts. One is fine and one is a recurring bug
source, and the difference is instructive.

[`register_optionflag`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L153)
is **append-only and idempotent**: registering a name that exists returns the
existing bit. It cannot be overwritten, so two libraries registering `NUMBER` agree
rather than fight. Its only sharp edge is ordering — ints are
`1 << len(OPTIONFLAGS_BY_NAME)` — which matters because typeshed hard-codes the
builtin values, so a flag registered *before* the builtins would change every
stdlib constant. Registering at import of the core rather than from a plugin hook
is what keeps that ordering stable, and it is also required because an
unregistered name makes a page fail to **parse**.

The docutils directive table is **overwrite-by-default and rebindable**. Sphinx's
`docutils_namespace()` restores a snapshot by rebinding the module attribute, so
the dict's *identity* changes and a cached boolean guard is wrong.
`Sphinx.add_directive` overwrites unconditionally with only a warning. The result
is that a directive class you registered may not be the one that ran.

**The rule extracted:** a global registry is acceptable when registration is
append-only and idempotent, and a liability when it is last-writer-wins. Where the
registry is someone else's and last-writer-wins, do not depend on having won —
depend on the *data* both writers produce. That is why ADR 0001 reads
`BlockAttributes` off the node rather than trusting its own directive classes to
have run: the attribute set is byte-compatible with what `sphinx.ext.doctest`
stamps, so either winner is fine.

`asyncio` reached the same conclusion about global indirection from the other
direction and is retiring `set_event_loop_policy` in favour of an explicit
`loop_factory=` argument — see [`14-asyncio.md`](14-asyncio.md).

## The nominal/structural trap, and the cheap way out

Typeshed's signatures demand classes: `DocTestFinder.__init__(parser: DocTestParser
= ...)`, `DocTestSuite(test_finder: DocTestFinder | None)`. The interpreter does
not — a duck-typed parser or finder runs fine. So a `Protocol` gives a third party
structural typing, and a nominal subclass keeps you *type-checkable* against the
stub.

The subclass does not buy passability. That is a matter of matching the call
signature: a finder whose `find()` takes a string first cannot be handed to
`DocTestSuite`, which passes a module — and subclassing does not change that.

Doing both costs nothing:

```python
class Frontend(t.Protocol):
    suffixes: t.ClassVar[frozenset[str]]

    def parse(
        self, text: str, path: pathlib.Path, *, settings: Settings
    ) -> ParseResult: ...


class DocutilsDocTestParser(
    doctest.DocTestParser
):  # nominal, for DocFileSuite(parser=...)
    ...
```

Sybil, xdoctest and stdlib each took one half. Taking both is the only reason this
is worth stating as a rule.

## What deserves a seam, and what does not

The project rule is that a new public API waits until a caller outside the module
needs it. Applied to the candidates that came up:

| Candidate | Verdict |
|---|---|
| `BlockKind` registry | **Yes.** Turns "a new block kind" from an edit to a method branching on string literals into adding a tuple. Which docutils node classes a kind arrives as stays in `markup/`, not on `BlockKind`, so the leaf keeps its stdlib-only contract |
| Output checker injection | **Yes.** The highest-demand seam, and the one Sybil closed entirely by hard-coding `checker=OutputChecker()` — adding one there requires subclassing two classes |
| `Frontend` protocol | **Yes.** Four implementations ship on day one (rST, MyST, text, Python docstrings) |
| `ExecutionProfile` (private) | **Yes, private.** [PR #59](https://github.com/git-pull/gp-libs/pull/59) adds top-level `await` — a second execution policy a `Literal["single", "exec"]` cannot express. Stays private until an out-of-tree caller exists |
| A per-example observer protocol | **No.** pytest gets failures through `report_*` and `MultipleDoctestFailures`; the CLI uses `summarize()`. No third consumer |
| A registry *object* with builders, digests and manifests | **No object, but there is a freeze.** The contributed block kinds, front ends and profiles are resolved into an immutable mapping alongside the frozen `Settings` facets, before collection begins; registering after that is an error. That is what ADR 0001's collection contract means by *frozen registry* — not a class with its own lifecycle |
| Entry-point plugin discovery | **Not in v1**, for want of a caller outside the package — *not* because it breaks xdist. Workers are fresh processes that re-run plugin loading with the same argv, so entry-point resolution is identical everywhere. What breaks determinism is nondeterministic *contribution*, such as a conftest registering conditionally on the environment |

The distinction those two rows turn on is worth stating once: **discovery is not
the hazard, nondeterminism is.** A registry populated identically in every process
satisfies [`12-pytest-xdist.md`](12-pytest-xdist.md)'s identical-collection
requirement no matter how it was populated; a registry whose contents depend on
which conftest happened to run, or on the environment, does not.

## Anchors

- [`register_optionflag`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L153) ·
  [`report_*` hooks](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1286-L1314) ·
  [`OutputChecker`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1690)
- [`_split_scope`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284) ·
  [`pytest_xdist_setupnodes` consumers](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26-L37)
- [`PytestAsyncioSpecs`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L90)
- [`AbstractEventLoop`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L254) ·
  [`set_event_loop_policy`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L817)
