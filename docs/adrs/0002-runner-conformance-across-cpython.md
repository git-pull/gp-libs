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
`IGNORE_EXCEPTION_DETAIL` — is run through both this runner and a stock
{class}`doctest.DocTestRunner`, asserting equality of `TestResults`, the captured
`report_*` text, `summarize()` output, and the accumulator contents.

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
