# pytest-asyncio

Pinned at [`v1.4.0`](https://github.com/pytest-dev/pytest-asyncio/tree/v1.4.0).

Read here as an **idiom exemplar**, not for async semantics. It is a mature,
widely-installed `pytest11` plugin that solves the same shape of problem this
project has: a per-item resource with a configurable lifetime, an opt-in mode, and
a default it needed to change without breaking anyone.

## Classification

A hook-driven behaviour plugin. It contributes no collector of its own for the
common case; it normalizes configuration into one question, answers it once, and
then injects behaviour through pytest's existing machinery rather than owning the
item class.

## Core data structures

```text
Mode(str, enum.Enum)            AUTO | STRICT                      [:82]
PytestAsyncioSpecs              its own hookspec namespace         [:90]
  pytest_asyncio_loop_factories(config, item) -> Mapping | None    firstresult
_ScopeName                      reuses pytest's scope vocabulary verbatim
```

`Mode` inheriting `str` is a small but deliberate choice: the ini value, the CLI
value and the internal enum are the same object, so no conversion layer exists to
drift.

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
   |  => the rest of the plugin has exactly ONE query path
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

**The `default=None` sentinel.** Every option is declared with `default=None`
([`:114`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L114),
[`:122`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L122),
[`:140`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L140))
rather than with its effective default. The plugin can therefore distinguish "the
user chose the current default" from "the user has not chosen", which is what
makes a future default change *announceable* — it warns only the second group.
`pytest_configure` uses exactly this to warn about an unset
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

**Session-wide errors raise `pytest.UsageError`; per-item errors raise
`ValueError`.** The severity matches the blast radius. A misspelled session
setting should stop the session; a bad per-item value should fail that item.

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
