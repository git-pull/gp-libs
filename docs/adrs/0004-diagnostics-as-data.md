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
value for this: `Diagnostic(level, code, message, path, line)`.

**Two mechanism assumptions in the first draft were wrong, and the fix is not
cosmetic.**

*There is no stable code to key on.* A docutils `system_message` carries a level
and text, and nothing semantically stable. So codes exist only for diagnostics
**this project emits**; docutils-originated messages arrive code-less and have to
be *classified* before they can be suppressed or promoted. The classifier is the
open question below, and it cannot be "key on the code", because for these
messages there is none.

*An observer does not silence the stream.* Attaching one is additive: the message
still reaches the warning stream. Turning reporter output into values needs three
settings together — `halt_level` above 4 (both to avoid the mid-parse abort and
because a halting message bypasses observer notification entirely),
`report_level` at 5 or `warning_stream` disabled to stop the write, and then the
observer.

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

Suppress narrowly, and only for the two classes a bare-docutils parse cannot
judge: unknown roles and unknown directives. "By code" is the intent; the
classifier that assigns a code to a docutils message is unsettled, so this
direction is not yet implementable.

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
- **What classifies a code-less docutils message.** The options are an owned,
  version-pinned message-text table with a test that fails on upstream rewording
  (and which must handle two dialects — reST's `Unknown directive type "x".` at
  ERROR/3 versus MyST's `Unknown directive type: 'x'` at WARNING/2), or
  pre-empting at the source by overriding the directive-dispatch path so the
  unknown case never becomes a reporter message at all. This is the decision
  ADR 0004 cannot ship without.
- **What promotes an unknown-directive message back to visible.** The first
  draft proposed "when the name is one this project registers", but that is
  inverted for the typo case — a misspelled `.. doctset::` is precisely *not* a
  registered name — and never fires for a foreign container whose body was
  swallowed unparsed. The rule that covers both is **body content**: promote when
  the swallowed body matches `DocTestParser._EXAMPLE_RE`. Near-miss-to-a-registered
  -name is a useful additional rule for the typo case, where the body check does
  not help.
- The body-content rule is reST-only as stated, because myst-parser discards the
  fence body. The Markdown equivalent is unsolved.
- Whether the CLI (`python -m doctest_docutils`) and the pytest plugin share one
  formatter or two.
