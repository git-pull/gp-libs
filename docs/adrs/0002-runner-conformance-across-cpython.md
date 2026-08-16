(adr-0002-runner-conformance-across-cpython)=

# ADR 0002: Runner conformance across CPython versions

Status: Draft
Date: 2026-08-02

## Context

{doc}`0001-typed-vanilla-doctest-core` has two execution lanes with different
compatibility claims.

Prompt-form blocks are ordinary {class}`doctest.DocTest` objects executed by
CPython's own {class}`doctest.DocTestRunner` loop. The core subclasses only the
reporting hooks that retain failures for an embedding host. It does not override
`run()` or `_DocTestRunner__run`.

Extended blocks such as Sphinx `testcode` cannot use that loop unchanged. CPython
compiles each example in `"single"` mode, while a `testcode` body may contain
several statements and requires `"exec"`. There is no stdlib execution mode to
select and therefore no exact-compatibility claim to make.

The supported interpreters also expose different result semantics. Python 3.10
increments `tries` only after an example passes its `SKIP` gate
([`Lib/doctest.py:1326-1337`](https://github.com/python/cpython/blob/v3.10.19/Lib/doctest.py#L1326-L1337)).
Python 3.14 increments `attempted` before the gate and records `skips` separately
([`Lib/doctest.py:1353-1379`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1353-L1379)).
`TestResults` gained its `skipped` attribute with that newer shape
([`Lib/doctest.py:114-126`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114-L126)).
The prompt lane must expose skipped examples without silently rewriting the
interpreter's own `attempted` value. The extended lane has no CPython count to
inherit and defines its own stable count below.

## Decision

Keep the two lanes structurally separate.

The prompt runtime delegates to CPython's untouched per-example loop with
`clear_globs=False`. Its reporter subclass may retain
{class}`doctest.DocTestFailure` and {class}`doctest.UnexpectedException`, and may
propagate exceptions selected by the host's `ExceptionPolicy`; it does not own
compilation, option merging, comparison, debugger setup, display hooks, linecache
patching, or result accounting.

An extended execution profile owns an independent, deliberately smaller runtime.
It accepts a fresh stock `DocTest` plus resolved `RuntimeSettings` and returns a
`RuntimeOutcome`. The initial `exec` runtime owns these semantics:

- merge runner flags with per-example options, then honor `SKIP` and fail-fast;
- derive active future flags from the live `globs`, compile in `"exec"` mode,
  and pass `dont_inherit=True` so the core module's future imports cannot leak;
- capture and restore stdout around every example;
- compare expected exceptions against the exception-only tail, including
  `SyntaxError` normalization and `IGNORE_EXCEPTION_DETAIL`, while retaining
  captured stdout for failure rendering;
- use the injected checker for comparison and retain stock failure objects;
- propagate host-owned outcomes through `ExceptionPolicy`; and
- leave group phase ordering, cleanup, and exception precedence to
  `run_group()`.

It does not update a `DocTestRunner` accumulator, call `report_*`, implement
`summarize()`, patch the debugger, or claim byte-for-byte output parity with the
prompt lane. A direct stdlib-shaped facade may translate `GroupResult` into the
version-specific accumulator needed by `summarize()`; that compatibility shim is
separate from execution.

## Conformance gate

The prompt lane is compatible by construction, but still runs on every supported
Python to catch subclass-state collisions and changes to reporter signatures.
Its tests assert stock object types, per-example option merging, fail-fast,
partial skips, repeated fresh materialization, and restoration of the shared
mapping contract.

The extended lane has a behavioral matrix rather than a comparison against
CPython's `"single"` compiler mode. Before it is accepted, the matrix covers:

| Behavior | Required assertion |
|---|---|
| pass and mismatch | stock failure objects, counts, and checker identity |
| future flags | no ambient inheritance; an explicitly imported feature persists through group `globs` |
| unexpected exception and `SyntaxError` | stock exception shape and stable traceback ownership |
| output before exception | defined capture and rendering behavior |
| all and partial skip | examples examined, including skips, plus an explicit skipped count on every interpreter |
| fail-fast and report-only-first | execution and reporting policies remain distinct |
| checker options | `IGNORE_EXCEPTION_DETAIL` and contributed checker behavior |
| process state | stdout is restored; debugger, display-hook, and linecache support is explicitly accepted or excluded |
| repeated calls | runtime-local state cannot leak between attempts |

Group cleanup after failure, pytest outcomes, fixture injection, reruns, and xdist
belong to host and `run_group()` acceptance tests. They are not evidence about an
individual execution profile.

Version handling uses capability probes, not `sys.version_info`. The prompt
runtime preserves CPython's own `attempted` value. The extended runtime counts
each example it examines, including an example skipped before compilation; on
interpreters whose `TestResults` cannot carry `skipped`, `run_group()` reconstructs
that value from the materialized test and stores it in `Counts`.

## Alternative rejected

Defining `_DocTestRunner__run` for extended profiles was rejected by the
implementation bakeoff. It couples a small `"exec"` requirement to private
accumulators, private outcome-recording arity, report-hook sequencing, debugger
machinery, and `summarize()` behavior that the host-neutral runtime does not use.
It is more code and a larger compatibility promise without making extended
syntax vanilla.

Cloning and patching CPython's code object or rebinding `doctest.compile`
process-wide remain rejected. Both make unrelated doctest execution depend on
global mutable state.

The spike still has two smaller CPython-private parser dependencies:
`DocTestParser._EXAMPLE_RE` recognizes prompt-form literal blocks and
`DocTestParser._EXCEPTION_RE` extracts the expected exception tail from paired
output. They do not couple execution to private runner state, but they are still
compatibility debt and need explicit probes across the supported Python matrix.
The legacy direct facade's use of `doctest._load_testfile` is outside the typed
core but belongs in the facade's own compatibility inventory.

## Consequences

- Ordinary doctests inherit CPython behavior directly rather than through a
  differential approximation.
- Extended profiles state their semantic subset and can manage attempt-scoped
  resources through their context manager.
- CPython's pre-3.13 and current prompt-lane skip counters remain observable;
  extended profiles expose their separate version-independent count through
  `Counts`.
- The direct compatibility facade needs a small version-shaped statistics shim
  if it promises stdlib `summarize()` and `master.merge()` behavior.
- The direct facade cannot reproduce the complete verbose
  `Trying`/`Expecting`/`ok` stream from `GroupResult`, because the core retains
  failures but not successful per-example reporter events. Failure and summary
  rendering remain stock-shaped.
- Each new execution profile owns its own behavioral matrix; adding async does
  not expand the prompt lane's maintenance surface.

## Open

- Complete the extended matrix for report-only-first and repeated runtime calls.
- Probe the two private parser regex contracts on every supported Python.
- Decide whether extended runtimes should reproduce doctest's debugger,
  display-hook, and linecache behavior or explicitly exclude interactive
  debugging.
- Define how a profile context-manager entry or exit failure is represented while
  still allowing an already-open cleanup profile to run.
