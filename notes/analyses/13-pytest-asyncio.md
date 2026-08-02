# pytest-asyncio

Pinned at [`v1.4.0`](https://github.com/pytest-dev/pytest-asyncio/tree/v1.4.0).

Read here as an **idiom exemplar**, not for async semantics. It is a mature,
widely-installed `pytest11` plugin that solves the same shape of problem this
project has: a per-item resource with a configurable lifetime, an opt-in mode, and
a default it needed to change without breaking anyone.

## Classification

A hook-driven behaviour plugin that **does** own its item class. It defines
`PytestAsyncioFunction(Function)`
([`:506`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L506))
with four concrete subclasses — `Coroutine`, `AsyncGenerator`,
`AsyncStaticMethod`, `AsyncHypothesisTest` — and a `pytest_pycollect_makeitem`
hookwrapper
([`:689-723`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L689-L723))
that substitutes them for every collected async `Function`.

That substitution-by-hookwrapper is itself the pattern worth noting: it swaps the
item class without owning collection, so pytest still decides *what* is a test
and the plugin only decides *how* it runs.

## Core data structures

```text
Mode(str, enum.Enum)            AUTO | STRICT                      [:82]
PytestAsyncioSpecs              its own hookspec namespace         [:90]
  pytest_asyncio_loop_factories(config, item) -> Mapping | None    firstresult
_ScopeName                      reuses pytest's scope vocabulary verbatim
```

`Mode` inherits `str`, but a conversion layer still exists and is exactly where
drift would occur: `_get_asyncio_mode`
([`:222-232`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L222-L232))
reads the CLI value, falls back to the ini value, and calls `Mode(val)` inside a
`try`, translating a `ValueError` into a {exc}`pytest.UsageError` that lists the
valid modes. The lesson is not "no conversion" — it is that the conversion
happens **once**, in one named function, with a good error.

Declaring its own `HookspecMarker("pytest")` namespace is the interesting one. A
third party extends pytest-asyncio by implementing a hook, not by subclassing
anything and not by mutating a registry — which sidesteps both the nominal-typing
trap and the process-global-registry trap.

## Data flow

```text
pytest_addoption      --asyncio-mode + asyncio_mode ini            [:108]
   |                  asyncio_default_fixture_loop_scope           [:137]
   |                  asyncio_default_test_loop_scope              [:143]
   |                  every one declared with default=None
   v
pytest_configure      validate scopes; addinivalue_line for the marker   [:295]
   |                  an unset default is DETECTED, not silently assumed
   v
_get_asyncio_mode(config)  -> Mode, resolved once                  [:222]
   |
   v
in AUTO mode: item.add_marker("asyncio")
   |  => marker presence becomes the single question downstream asks
   v
fixture/loop resolution by scope, then pyfunc call wrapping
```

## Extension seams

| Seam | Kind |
|---|---|
| `asyncio_mode` ini + `--asyncio-mode` CLI | configuration |
| `@pytest.mark.asyncio` | marker, registered via `addinivalue_line` |
| `asyncio_default_fixture_loop_scope`, `asyncio_default_test_loop_scope` | configuration, reusing pytest's scope names |
| `pytest_asyncio_loop_factories` | its own `firstresult` hookspec |
| `@pytest_asyncio.fixture(loop_scope=...)` | decorator, stamping `_loop_scope` on the function |

## What is worth stealing

**The `default=None` sentinel, used selectively.** Of the six options
`pytest_addoption` declares
([`:108-147`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L108-L147)),
three carry `None` and three carry their effective default — so this is a
technique applied where it earns its keep, not a blanket rule.

It earns its keep on the options whose default the project intends to move. A
`None` lets the plugin distinguish "the user chose the current default" from "the
user has not chosen", which is what makes a future change *announceable* — only
the second group is warned. `pytest_configure` does exactly that for an unset
`asyncio_default_fixture_loop_scope`
([`:296-301`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L296-L301)).

This project has the same problem coming: ADR 0001's vocabulary change renames
`namespace_scope` to `share`, and any future move of the block-vs-document default
needs the same mechanism.

**Normalize, then query once.** In `AUTO` mode the plugin literally adds the
marker it would otherwise have to special-case, so downstream code has one
question with one answer shape. The alternative — branching on mode at every read
site — is what produces the "two components disagree about the current setting"
class of bug.

**Reuse the host's vocabulary rather than inventing a parallel one.** Loop scope
uses pytest's own `function`/`class`/`module`/`package`/`session` ladder and its
scope names verbatim. It does not invent a third word for lifetime. Compare the
current `namespace_scope`/`namespace_items` naming, which collides with two pytest
concepts at once.

**Session-wide errors raise {exc}`pytest.UsageError`.** An invalid `asyncio_mode`
and an invalid loop-scope ini value both raise it, and both are reached from
session-level config in `pytest_configure`. A misspelled session setting stops the
session, which is the right blast radius for a value that would otherwise
mis-apply to every item.

The mirror rule — per-item errors raising something narrower — is *not* something
this plugin demonstrates cleanly, so do not cite it as precedent. Marker parsing
is one function with one blast radius. The session half is the transferable part.

## What it cannot tell us

Its resource — an event loop — is cheap to create, has no cross-process identity
problem, and never needs to be scheduled onto a particular worker. It therefore
has nothing to say about the distribution question that dominates this project's
design, and its scope model should not be copied on that axis.

## Anchors

- [`Mode`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L82) ·
  [`PytestAsyncioSpecs`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L90)
- [`pytest_addoption`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L108) ·
  [`_get_asyncio_mode`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L222) ·
  [`pytest_configure`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L295)
- [`_make_asyncio_fixture_function`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L210)
