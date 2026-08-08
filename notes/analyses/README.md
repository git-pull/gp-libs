# Doctest ecosystem structural analyses

Structural analysis of how the systems `doctest_docutils` sits between are built —
their core data structures, data flows, extension seams, and configuration models.
These are research notes. They inform the ADRs in `docs/adrs/` and decide nothing
themselves.

The question they exist to answer: a doctest engine that must be vanilla-compatible
at the core, pluggable, usable as a pytest plugin, usable with docutils and
myst-parser, *and* speak all three communities' idioms is standing on three
upstreams with three separate extension models and three overlapping vocabularies.
What exactly does each of them require, and where do they contradict each other?

## Method

1. **Portable citations first.** Every external reference is a deep link to a
   specific file **pinned at a git tag** — never `main`, `master`, `HEAD` or a bare
   SHA. Line anchors are only used on a pinned ref, because they are meaningless
   without one. These links are the reproducible source surface for the analysis.
2. **Source review second.** Confirm and deepen against checked-out source with
   `rg`/`fd`. Local notes may inform drafting; tracked notes must be readable and
   verifiable without a workstation path.
3. **Execute the load-bearing claims.** Anything an ADR rests on is run, not read.
   Where a note says "verified", a snippet was executed and its output recorded.

## Pinned versions

| Project | Repo | Ref |
|---|---|---|
| CPython (`doctest`, `asyncio`) | `python/cpython` | `v3.14.2` |
| pytest | `pytest-dev/pytest` | `9.1.1` |
| pytest-xdist | `pytest-dev/pytest-xdist` | `v3.8.0` |
| pytest-asyncio | `pytest-dev/pytest-asyncio` | `v1.4.0` |
| Sphinx | `sphinx-doc/sphinx` | `v8.2.3` — what this project resolves. `v9.0.0` is cited only for the bare-node group fallback change |
| MyST-Parser | `executablebooks/MyST-Parser` | `v5.1.0` on Python ≥ 3.11; `v4.0.1` below |
| Sybil | `simplistix/sybil` | `10.0.1` |
| xdoctest | `Erotemic/xdoctest` | `v1.3.2` |
| typeshed | `python/typeshed` | `8c7256c` (no tags; commit reachable from trunk) |
| docutils | SourceForge (the GitHub clones are third-party mirrors) | `docutils-0.21.2` |

## Files

- [`00-taxonomy.md`](00-taxonomy.md) — the design axes, as a classification matrix.
- Per-system structural docs: [`10-cpython-doctest.md`](10-cpython-doctest.md),
  [`11-pytest-doctest.md`](11-pytest-doctest.md),
  [`12-pytest-xdist.md`](12-pytest-xdist.md),
  [`13-pytest-asyncio.md`](13-pytest-asyncio.md),
  [`14-asyncio.md`](14-asyncio.md),
  [`15-sphinx-ext-doctest.md`](15-sphinx-ext-doctest.md),
  [`16-docutils-myst.md`](16-docutils-myst.md),
  [`17-prior-art.md`](17-prior-art.md).
- Cross-cutting: [`20-data-structures.md`](20-data-structures.md),
  [`21-data-flows.md`](21-data-flows.md),
  [`22-extension-seams.md`](22-extension-seams.md),
  [`23-namespace-scope-and-test-identity.md`](23-namespace-scope-and-test-identity.md),
  and [`24-implementation-bakeoff.md`](24-implementation-bakeoff.md).
- [`90-bibliography.md`](90-bibliography.md) — every pinned anchor cited by the
  ADRs, in one place.

Each per-system doc follows the same section order — classification · core data
structures · data flow · extension seams · configuration · what it cannot do ·
anchors — so the systems are directly comparable, and the cross-cutting docs can
line them up column by column.

`14-asyncio.md` is included even though `asyncio` has nothing to do with doctests.
It is the stdlib's own worked example of a pluggable architecture built out of
protocols, an abstract base, a policy indirection and a runner, by roughly the same
people and in roughly the same era as `doctest`'s extension model. Reading the two
side by side is the cheapest available answer to "what does the standard library
consider a good seam, and why does `doctest` have so few of them?"
