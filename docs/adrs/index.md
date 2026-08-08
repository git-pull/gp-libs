(adrs)=

# Architecture Decision Records

Significant design decisions for `doctest_docutils` and
`pytest_doctest_docutils`, and their rationale.

These records govern the shape of the doctest engine: what it produces, what it
may reach into, and what vocabulary it speaks. A record states the context that
forced a decision, the decision itself, what it costs, and what it rules out —
so a later reader can tell a deliberate constraint from an accident.

Supporting structural research lives in `notes/analyses/`. It decides nothing and
is cited by these records as evidence.

## Conventions

**Numbering** is sequential and permanent. A record is never renumbered, and a
superseded one is marked rather than deleted.

**Status** is one of `Draft`, `Proposed`, `Accepted`, `Superseded by NNNN`.

**Source links are pinned.** Every citation of an external project names a git
tag, or a commit reachable from that project's trunk where it publishes no tags.
Line anchors are only used on a pinned ref, because they are meaningless without
one, and a `blob/master` link rots silently — the file moves, lines shift, and
the anchor lands on unrelated code while still resolving.

```{toctree}
:maxdepth: 1

0001-typed-vanilla-doctest-core
0002-runner-conformance-across-cpython
0003-rejecting-per-block-items
0004-diagnostics-as-data
0005-line-recovery-for-nested-blocks
0006-pytest-private-api-compatibility
0007-host-plugin-registration-lifecycle
```
