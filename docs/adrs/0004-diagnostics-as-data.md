(adr-0004-diagnostics-as-data)=

# ADR 0004: Diagnostics as data

Status: Draft
Date: 2026-08-02

## Context

Parsing a page currently writes docutils reporter output straight to stderr,
interleaved with pytest's own output and attributable to nothing. Two failure
modes follow from the default settings.

A level-4 message raises `SystemMessage` mid-parse and aborts collection of the
file, so one malformed construct takes down a page whose other blocks are fine.

More quietly, a `.. doctest::` block carrying an unknown option collects **zero**
tests and the session exits green. A page that checks nothing reports the same
way as a page that passes.

{doc}`0001-typed-vanilla-doctest-core` gives the front-end layer a second return
value for this: `Diagnostic(level, code, message, path, line)`, produced by
setting `halt_level` past the abort threshold and attaching a reporter observer.
Suppression and promotion key on the stable `code`, never on message text.

## Question

Which diagnostics are shown by default?

The naive answer — show everything — was measured against this project's own
`docs/` and produces well over a hundred messages per run, almost all of them
`Unknown interpreted text role` and `Unknown directive type` for roles and
directives that Sphinx supplies and a bare-docutils parse structurally cannot
resolve. Those are false positives. Emitting them is noise-as-policy, and users
would learn to ignore the channel that also carries real errors.

The opposite error is worse: suppressing one code too many turns a broken page
into a silent zero-test page, which is the exact condition this ADR exists to
surface.

## Direction

Suppress by code, narrowly, and only for the two classes a bare-docutils parse
cannot judge: unknown roles and unknown directives.

Every diagnostic raised by this project's own layers defaults to visible, and
`level="error"` from those layers fails collection with the file and line named.
A page whose only block fails to parse, and a page with a malformed `:options:`
value, must both produce a collection error rather than collecting nothing and
passing.

Expose promotion and suppression by code so a project can tune the set without a
global on/off switch.

## Open

- Whether diagnostics surface as {class}`pytest.PytestWarning` subclasses, giving
  `-W error::` control for free, or as a dedicated report section.
- Whether an unknown-directive diagnostic should be promoted when the directive
  name is one this project registers — that case is not Sphinx supplying it, it
  is a registration that did not happen, which is the GH-48 failure mode.
- Whether the CLI (`python -m doctest_docutils`) and the pytest plugin share one
  formatter or two.
