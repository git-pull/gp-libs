(adr-0005-line-recovery-for-nested-blocks)=

# ADR 0005: Line recovery for nested blocks

Status: Draft
Date: 2026-08-02

## Context

docutils does not report a usable line for every node, and what it reports
differs by front-end and by version.

At **docutils 0.21.2**, which this project currently pins, a bare `>>>` block
nested in a `.. note::`, a list item, a block quote or a `{tab}` directive
reports `line=None, source=None`. A top-level reStructuredText `doctest_block`
reports its **last** line. A MyST fence reports its **first** line. An
`.. include::`-ed block numbers against the *included* file.

{doc}`0001-typed-vanilla-doctest-core` handles all of this honestly rather than
approximately: `Block.line` is nullable, the per-front-end meaning is normalized
inside the front-end that knows it, `Block.path` carries the file the text
actually lives in, and a block with no recoverable line propagates
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

## Decision

**Raise the docutils floor instead.**

docutils 0.22 fixed the underlying defect upstream: a nested block reports a real
line, and top-level and nested blocks agree on reporting the **first** line
rather than the last. Every case this record was invented to work around is
resolved by a floor bump, with no probe, no substitution and no fallback path.

The cost is that docutils ≥ 0.22 requires Sphinx ≥ 9.1, so this is a coordinated
dependency move rather than a one-line pin change.

## Consequences

The nullable `Block.line` stays. It is not a workaround for this defect; it is
the honest representation of a front-end that may legitimately not know, and
`.. include::` attribution still needs `Block.path` regardless of version.

The line-convention normalization in `markup/` gets *simpler* at the new floor —
both reStructuredText and MyST report the first line — but the normalization
layer stays, because the conventions still differ below the floor and a front-end
is the right place to know which it is dealing with.

Every line-convention claim elsewhere in these records is version-qualified.
A statement about "docutils" that does not name a version is a bug in the
statement.

## Open

- Whether to raise the floor now or support both, since 0.21.2 is what the
  project pins today. Supporting both means keeping the normalization branch and
  documenting two behaviours for the same page.
- Whether the Sphinx ≥ 9.1 move belongs in this record or its own. It changes the
  default group an unargumented block joins, which is a semantics change beyond
  line numbers.
- Whether tests should pin exact `(path, line)` for a bare block nested in a
  `.. note::`, a list item, a block quote and a `{tab}` directive. They should —
  they are the regression net for the floor, and this repository already has
  `{tab}` coverage from the GH-48 regression.
