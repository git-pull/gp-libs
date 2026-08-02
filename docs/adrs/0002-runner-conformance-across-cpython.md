(adr-0002-runner-conformance-across-cpython)=

# ADR 0002: Runner conformance across CPython versions

Status: Draft
Date: 2026-08-02

## Context

{doc}`0001-typed-vanilla-doctest-core` decides that the runner owns the
per-example loop by defining `_DocTestRunner__run` in a subclass, rather than
cloning CPython's code object or rebinding `doctest.compile` process-wide.

Owning the loop means owning the private state it writes into, and that state has
changed shape inside this project's supported interpreter range. Three
divergences are known:

**The outcome accumulator changed name and arity.** On 3.10 through 3.12 it is
`__record_outcome(self, test, f, t)` writing into `self._name2ft`; on 3.13 and
later it is `__record_outcome(self, test, failures, tries, skips)` writing into
`self._stats`
([`Lib/doctest.py:1485`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1485)).
A loop that calls the wrong one leaves `summarize()` reporting zeros for a
passing file — a silent, total failure of the reporting path.

**`TestResults` gained a third value that is not a tuple field.** It carries
`skipped` as an extra instance attribute
([`Lib/doctest.py:114`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114)),
so `TestResults(f, a, skipped=s)` works on 3.13+ and raises on earlier versions.

**`report_skip` does not exist at v3.14.2.** The runner has only `report_start`,
`report_success`, `report_failure` and `report_unexpected_exception`
([`Lib/doctest.py:1286-1314`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1286-L1314)).
It appears in later prereleases, so a loop must probe rather than assume in
either direction.

A fourth risk has no current instance but would be silent: a CPython refactor
that inlines the loop into `run()` would route execution back to stdlib. That is
invisible for prompt-form blocks and immediately broken for `{testcode}`.

## Question

How is an owned per-example loop proven equivalent to the interpreter's own,
continuously, without a `sys.version_info` ladder?

## Direction

A differential conformance harness, run in CI on every supported interpreter,
gating the build step that lands the runner.

A fixed case matrix — pass, fail, unexpected exception, `SyntaxError`, all
examples skipped, partially skipped, `FAIL_FAST`, `REPORT_ONLY_FIRST_FAILURE`,
`IGNORE_EXCEPTION_DETAIL`, and an exec-mode body — is run through both this
runner and a stock {class}`doctest.DocTestRunner`, asserting the captured
`report_*` text, `summarize()` output, the accumulator contents, and the result
as `(failed, attempted, skipped)`.

**Assert the triple, not `TestResults` equality.** `TestResults` is a two-field
namedtuple carrying `skipped` off-tuple, so `==` compares only two of the three
values and a skip-count regression passes silently. `attempted` is also
incremented *before* the `SKIP` check, so a skip that wrongly executes moves
neither counter — it is invisible to both the tuple and to `summarize()` at zero
failures, and only the `report_*` text distinguishes it.

The exec-mode case is the one the two runners are *meant* to disagree on, and it
still compares against stock. `compile()` raises on a multi-statement body, but
that call sits inside the loop's own `try`
([`Lib/doctest.py:1398-1408`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1398-L1408)),
so a stock {class}`doctest.DocTestRunner` catches the `SyntaxError` and records
it as an unexpected exception rather than propagating it: one
`report_unexpected_exception` call, `TestResults(failed=1, attempted=1)`, and
`_stats` at `(1, 1, 0)`. Only {class}`doctest.DebugRunner` — and pytest's runner
beneath it — converts that into a raise, as
{exc}`doctest.UnexpectedException`. So the case is asserted as a pair: stock
records the failure, this runner records a pass. A regression that silently
reverts to `"single"` mode shows up as the two converging.

**What else belongs in the matrix, and what does not.** Add `report_*` hook
events — the only channel that distinguishes a skip which wrongly *executed*,
since `attempted` increments before the `SKIP` check and neither counter moves —
and repeated runs of one test, which exercise accumulator arithmetic across
calls.

Cross-block `FAIL_FAST` and cleanup aggregation stay out. Both are properties of
`run_group()` rather than of the per-example loop, so a stock runner offers
nothing to compare them against; they belong to
{doc}`0001-typed-vanilla-doctest-core`'s item-lifecycle tests. A
{exc}`pytest.skip` raised inside an example and a debugger exit are likewise
pytest-layer concerns, testable only through a pytest session.

Version handling is by capability probe, never by version comparison, so a
backport, a vendored interpreter or a fork behaves correctly rather than by
coincidence. {doc}`0001-typed-vanilla-doctest-core` rejects an import-time guard
that raises: a `pytest11` plugin that aborts at import takes down suites whose
majority of tests never touch a doctest.

## Open

- Whether the harness asserts on `report_*` text verbatim, or on a normalized
  form — verbatim is stricter and will churn when CPython adjusts wording.
- Whether a probe failure degrades to stdlib's loop with a diagnostic, or fails
  the affected items loudly. Degrading is silent for prompt-form blocks, which is
  the argument against it.
- The floor: whether supporting 3.10's `_name2ft` shape is worth its shim once
  that version reaches end of life.
