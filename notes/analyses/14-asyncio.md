# `asyncio` — the standard library's own pluggable architecture

Pinned at [`v3.14.2`](https://github.com/python/cpython/tree/v3.14.2/Lib/asyncio).

`asyncio` has nothing to do with doctests. It is here because it is the standard
library's worked example of a *deliberately* pluggable subsystem, written by
roughly the same community and shipped in the same tree as `doctest`. Setting the
two side by side answers a question the other notes cannot: when CPython wants an
extension point, what does it build — and why does `doctest` have almost none?

## Classification

A layered subsystem with four distinct seam kinds, none of which `doctest` uses:
an abstract base class defining the contract, duck-typed callback interfaces, a
policy indirection for selecting an implementation, and a context-manager runner
that owns lifecycle.

## Core data structures

```text
Handle / TimerHandle            a scheduled callback                [events.py:34, :141]
AbstractEventLoop               the CONTRACT, ~90 methods           [events.py:254]
BaseEventLoop(AbstractEventLoop)   the shared implementation        [base_events.py:417]
Future                          a result slot with callbacks        [futures.py:31]
Task(Future)                    a coroutine driven by a loop        [tasks.py:56]
Runner                          context manager owning a loop       [runners.py:21]
BaseProtocol / Protocol / BufferedProtocol / DatagramProtocol / SubprocessProtocol
                                what YOU implement                  [protocols.py:9, :66, :109, :162, :177]
BaseTransport / ReadTransport / WriteTransport / Transport / ...
                                what the LOOP implements            [transports.py:9, :46, :72, :148]
```

## The four seam kinds

**1. An abstract base as a published contract.** `AbstractEventLoop`
([`events.py:254`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L254))
names every method an event loop must provide, separately from
`BaseEventLoop`, which implements most of them. A third party writing uvloop
implements the *contract*, not a subclass of the shipped implementation. Compare
`doctest`, where the contract and the implementation are the same class, so
`DocTestFinder(parser=...)` demands the class rather than the shape.

**2. Paired duck-typed roles.** `Protocol` is what the user writes; `Transport` is
what the loop provides. Neither is registered anywhere, neither is checked with
`isinstance`, and the split is by *direction of the call*: the transport is called
by you, the protocol is called by the loop. This is the cheapest possible
extension mechanism — two documented method vocabularies — and it has carried
third-party HTTP, TLS and subprocess stacks for a decade.

**3. A policy indirection, and its retirement.** `get_event_loop_policy` and
`set_event_loop_policy` sit at
[`events.py:804`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L804)
and [`:817`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L817),
now delegating to private `_get_event_loop_policy` / `_set_event_loop_policy`
([`:798`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L798),
[`:808`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L808)) —
the public spellings are on the way out. That is the most instructive thing in
this file. A process-global, mutable indirection for "which implementation should
this program use" was shipped, was widely misused, and is being replaced by
passing the choice explicitly: `asyncio.run(main, loop_factory=...)`
([`runners.py:169`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L169)).

The lesson transfers directly. A process-global mutable registry is the seam you
regret. docutils' directive table is the same shape and has the same problems —
see [`16-docutils-myst.md`](16-docutils-myst.md).

**4. A runner that owns lifecycle.** `Runner`
([`runners.py:21`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L21))
is a context manager that creates the loop, runs the work, cancels stragglers
([`:207`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L207))
and shuts down cleanly. Global state that must be restored lives in one `finally`
owned by one object.

`doctest.DocTestRunner.run` does exactly this for `sys.stdout`, `pdb.set_trace`,
`linecache.getlines`, `sys.displayhook` and `PYTHON_COLORS`
([`doctest.py:1534-1573`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1534-L1573)).
It is the one place `doctest` and `asyncio` agree on architecture, and it is
precisely why ADR 0001 takes over `__run` but leaves `run()` alone: the lifecycle
owner should keep owning the lifecycle.

## Cross-cutting: what `doctest` would look like with `asyncio`'s seams

| `asyncio` | `doctest` equivalent | Present? |
|---|---|---|
| `AbstractEventLoop` as a separate contract | an ABC or `Protocol` for finder/parser/checker | no — the class *is* the contract |
| `Protocol`/`Transport` duck-typed roles | `OutputChecker` is close: a documented method vocabulary, injected | partly |
| policy indirection | none | no |
| `Runner` owning lifecycle | `DocTestRunner.run`'s save/restore | yes |
| explicit `loop_factory=` replacing global policy | `parser=`, `checker=`, `test_finder=` injection | yes, and it is the healthy part |

The gap is the first row, and it is the concrete reason
`DocutilsDocTestFinder` cannot be handed to `DocTestSuite(test_finder=...)` today
despite exposing a compatible `find()`. ADR 0001's answer — declare `Protocol`s
*and* subclass the stdlib classes nominally — is the cheap way to have both, and
it costs nothing at runtime.

## Anchors

- [`AbstractEventLoop`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L254) ·
  [`BaseEventLoop`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/base_events.py#L417)
- [`get_event_loop_policy`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L804) ·
  [`set_event_loop_policy`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L817)
- [`BaseProtocol`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/protocols.py#L9) ·
  [`Transport`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/transports.py#L148)
- [`Runner`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L21) ·
  [`run(main, *, loop_factory=None)`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L169) ·
  [`_cancel_all_tasks`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L207)
- [`Future`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/futures.py#L31) ·
  [`Task`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/tasks.py#L56)
