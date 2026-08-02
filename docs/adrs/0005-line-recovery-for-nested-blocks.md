(adr-0005-line-recovery-for-nested-blocks)=

# ADR 0005: Exact line recovery for nested blocks

Status: Draft
Date: 2026-08-02

## Context

docutils does not report a usable line for every node, and what it does report
differs by front-end.

A bare `>>>` block nested in a `.. note::`, a list item, a block quote or a
`{tab}` directive reports `line=None, source=None`. A top-level reStructuredText
`doctest_block` reports its **last** line; a MyST fence reports its **first**. An
`.. include::`-ed block numbers against the *included* file.

{doc}`0001-typed-vanilla-doctest-core` handles all three honestly rather than
approximately. `Block.line` is nullable, the per-front-end meaning is normalized
inside the front-end that knows it, `Block.path` carries the file the text
actually lives in, and a block with no recoverable line propagates
`DocTest.lineno=None` into pytest's `EXAMPLE LOCATION UNKNOWN` branch.

That is correct but not maximal. A nested block's failure says the location is
unknown when the information exists in the parser and was discarded.

## Question

Can the exact line be recovered for a nested block without a fragile dependency?

The mechanism identified is per-instance substitution of
`docutils.parsers.rst.Parser.state_classes`. `state_classes` is an instance
attribute, so substitution is fully scoped to one parse with no process-global
mutation — unlike the directive registry, which has no such scoping.

It also depends on undocumented docutils structure, and a refactor upstream would
break it as `None` spans rather than as an exception.

## Direction

Land it last, as a strictly optional improvement behind a feature probe.

When the expected structure is absent, fall back to `node.line` normalization and
emit `line=None`. Degrading to an honest disclaimer is acceptable; degrading to a
fabricated number is not, and that is the whole reason this is separable from
{doc}`0001-typed-vanilla-doctest-core` rather than part of it.

Pin with tests asserting exact `(path, line)` for a bare block nested in each of
the four constructs, plus a test that forces the probe to fail and asserts the
fallback yields `lineno=None`.

## Open

- Whether the same technique gives MyST nested blocks anything, or whether
  markdown-it's token stream already carries enough.
- Whether `.. include::` line attribution needs the same treatment or is already
  correct once `Block.path` is respected.
- Whether the probe result is reported anywhere, so a user can tell which mode
  produced a given report.
