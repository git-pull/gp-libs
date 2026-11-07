(adr-0005-line-recovery-for-nested-blocks)=

# ADR 0005: Line recovery for nested blocks

Status: Draft
Date: 2026-08-02

## Context

docutils does not report a usable line for every node, and what it reports
differs by front-end and by version.

At **docutils 0.21.2** — which this project does not pin but does resolve, via
its Sphinx and myst-parser constraints — a bare `>>>` block
nested in a `.. note::`, a list item, a block quote or a `{tab}` directive
reports `line=None, source=None`. A top-level reStructuredText `doctest_block`
reports its **last** line. A MyST fence reports its **first** line. An
`.. include::`-ed block numbers against the *included* file.

{doc}`0001-typed-vanilla-doctest-core` handles all of this honestly rather than
approximately: `ParsedBlock.line` is nullable, the per-front-end meaning is
normalized inside the front-end that knows it, `ParsedBlock.path` carries the
file the text actually lives in, and a block with no recoverable line propagates
`DocTest.lineno=None` into pytest's `EXAMPLE LOCATION UNKNOWN` branch.

That is correct but not maximal. A nested block's failure says the location is
unknown when the parser knew it and threw it away.

## The mechanism this record originally proposed does not work

The idea was to substitute `docutils.parsers.rst.Parser.state_classes` per
parser instance, on the reasoning that `state_classes` is an instance attribute
and therefore scoped to one parse.

It fails on two counts, both checked:

**It does not reach nested blocks.** A nested parse builds its state machine from
`nested_sm_kwargs`, so a substitution applied only to the top-level
`state_classes` never reaches the constructs that need it — which are exactly the
constructs with the missing lines.

**It is not scoped.** `RSTState.nested_sm_cache` is a shared *class* attribute,
so substituted classes leak into subsequent parses that did not ask for them.
The claim that substitution is "fully scoped to one parse with no process-global
mutation" is wrong.

## Direction

**Raise the docutils floor instead** — but that is **support policy, not core
architecture**. Nothing in {doc}`0001-typed-vanilla-doctest-core` depends on the
answer: a nullable line is the honest representation either way, and the floor
only decides how often it is `None`. This record can stay open indefinitely
without blocking the design.

docutils 0.22 fixed the underlying defect upstream: a nested block reports a real
line, and top-level and nested blocks agree on reporting the **first** line
rather than the last. Every case this record was invented to work around is
resolved by the floor, with no probe, no substitution and no fallback path.

Getting there is three moves, and the second is upstream of this repository:

1. **Raise `requires-python` to `>= 3.11`.** Sphinx 9.0 is the first release that
   permits docutils 0.22, and it declares `requires-python >= 3.11`. Dropping 3.10
   also touches the classifiers, the mypy and ruff target versions, and the CI
   matrix.
2. **Ship a `gp-sphinx` release that widens its `sphinx < 9` cap.** This is the
   binding constraint today, and it is not in this repository. With the cap in
   place, a resolver asked for `docutils >= 0.22` reports the requirements
   unsatisfiable.
3. **Then** declare `docutils >= 0.22, < 0.23`. An open-ended floor breaks the
   moment a resolver reaches 0.23.

Resolved versions per interpreter, with `docutils >= 0.22` requested:

| Python | docutils | myst-parser | Sphinx |
|---|---|---|---|
| 3.10 | 0.23 | 0.13.6 | 3.5.3 — a degenerate backtrack, not viable |
| 3.11 | 0.22.4 | 5.1.0 | 9.0.4 |
| 3.12–3.14 | 0.22.4 | 5.1.0 | 9.1.0 |

Today's lock resolves Sphinx 8.1.3 on Python 3.10 and 8.2.3 elsewhere, and
neither permits docutils 0.22.

## Consequences

The nullable `ParsedBlock.line` stays. It is not a workaround for this defect;
it is the honest representation of a front-end that may legitimately not know,
and `.. include::` attribution still needs `ParsedBlock.path` regardless of
version.

The line-convention normalization in `markup/` gets *simpler* at the new floor —
both reStructuredText and MyST report the first line — but the normalization
layer stays, because the conventions still differ below the floor and a front-end
is the right place to know which it is dealing with.

Every line-convention claim elsewhere in these records is version-qualified.
A statement about "docutils" that does not name a version is a bug in the
statement.

## Open

- **The blocking question: does this project drop Python 3.10?** Everything else
  here is downstream of that, and it is a support-matrix decision that outlives
  this record. Until it is settled, "raise the floor" is a direction, not a
  decision — which is why this record's status stays `Draft`.
- Whether to raise the floor at all or support both, since docutils 0.21.2 is
  what resolves today. Supporting both means keeping the normalization branch and
  documenting two behaviours for the same page.
- Sequencing with the `gp-sphinx` cap. That release has to land first, and this
  repository does not control it.
- Whether the Sphinx move belongs in this record or its own. Sphinx **9.0**
  changed the fallback group for a bare, unstamped `doctest_block` from
  `['default']` to `[doctest_test_doctest_blocks]`; directives always stamp
  `groups`, so unargumented *directives* are unaffected. 9.x also differs in
  fail-fast and result propagation. All of that is semantics beyond line numbers.
- Whether tests should pin exact `(path, line)` for a bare block nested in a
  `.. note::`, a list item, a block quote and a `{tab}` directive. They should —
  they are the regression net for the floor, and this repository already has
  `{tab}` coverage from the GH-48 regression.
