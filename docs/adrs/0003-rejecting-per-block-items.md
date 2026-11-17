(adr-0003-rejecting-per-block-items)=

# ADR 0003: Rejecting per-block items over a shared mapping

Status: Draft
Date: 2026-08-02

## Context

[PR #87](https://github.com/git-pull/gp-libs/pull/87) proposes two settings that
together choose how a page's blocks are collected. One of them,
`doctest_docutils_namespace_items = per-block`, keeps a node id for every block
of a shared page and hands those blocks one live `globs` mapping rather than
merging them into a single test.

**Neither setting has shipped.** Both live on an open branch, in no release and
on no tag. There is nothing to deprecate, and this record does not propose a
deprecation — it records why the shape should not ship.

## The shape, and why it is attractive

`per-block` answers a real complaint about merging. Merging a group into one
`DocTest` collapses N node ids into one, merges fixture lifetime across the whole
group, and makes the failure gutter span the page. Keeping one id per block fixes
all three, and on a large documentation tree the difference is the bulk of the
suite's visible granularity.

## Why it should not ship

**A node id that cannot be selected is not a node id.** Selecting block three of
a stateful page raises `NameError`, because the blocks that bound the names it
reads did not run. The id promises an addressable unit and does not deliver one.

**A live mapping cannot cross a process.** Only execnet-serializable builtins
reach an xdist worker, so the shape needs a scheduler that keeps a page whole —
and the only affinity primitive in xdist is
[`_split_scope(nodeid) -> str`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284).
Under a user-typed `--dist load` there is no scheduler to influence, so the
options collapse to refusing the run.

**A live mapping cannot survive an item running twice.** A retry re-runs a block
against globals it already mutated, so an expectation true only on the second
attempt reports as a pass. Guarding that means refusing reruns.

**A worker crash re-runs only the uncompleted tail** of a work unit, on a fresh
process — so blocks 3..N of a shared group run against an empty mapping, and
worker restarts are on by default. This one has no guard at all.

Those four are why the branch also carries a worker-count fork, a page-inference
heuristic over node-id strings, a scheduler substitution, a scheduler refusal and
a rerun refusal. The guards are the cost of the shape, not incidental.

## Decision

Do not ship per-block items over a shared mapping, under this or any spelling.

{doc}`0001-typed-vanilla-doctest-core` reaches the same granularity goal from the
other side: one item per group, holding one `DocTest` per block. That gives
per-block failure locations, gutters and "location unknown" without a shared
mapping ever becoming schedulable, so none of the four guards is needed.

What it does not give is a per-block *outcome* or a per-block *node id*. That
limit is honest and is recorded in {doc}`0001-typed-vanilla-doctest-core`'s
outcome contract, rather than papered over with an id that raises when used.

## Consequences

Because nothing shipped, there is no migration path to write, no deprecation
warning to add and no downstream grep to run.

## Open

- Whether a human-facing block *label* — in failure text and the report header,
  never as a node id — is worth adding later, so a reader can find the failing
  block without the design promising `-k` isolation. Not in a first version.
- Whether `--doctest-docutils-namespace-scope` should be renamed to
  `--doctest-docutils-share` before or after this architecture lands.
  {doc}`0001-typed-vanilla-doctest-core` settles the vocabulary; the rename is
  independently schedulable and, since neither spelling has shipped, cheap.
