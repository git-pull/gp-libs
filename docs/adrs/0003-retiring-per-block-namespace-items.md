(adr-0003-retiring-per-block-namespace-items)=

# ADR 0003: Retiring `namespace_items = per-block`

Status: Draft
Date: 2026-08-02

## Context

`doctest_docutils_namespace_items` selects between `merged` (the default: a group
collects as one test) and `per-block` (each block keeps its own node id while the
blocks share one live `globs` mapping).

{doc}`0001-typed-vanilla-doctest-core` makes the setting unnecessary by
decoupling the two axes it was invented to trade between: one pytest item per
group, with one {class}`doctest.DocTest` per block inside it. That gives
`per-block`'s per-block failure locations, gutters and `SKIPPED` reporting
without `per-block`'s shared live mapping.

It also removes `per-block`'s cost. A live mapping is a Python object, so it
neither crosses a worker process nor survives an item running twice. Guarding it
is the sole reason `_worker_count`, `_shared_page`, `_is_page`,
`_splitting_scheduler` and both xdist hooks exist.

The setting's remaining distinguishing feature is a node id per block — and those
ids raise `NameError` when selected alone, because selecting one block does not
run the blocks that bound the names it reads. A node id that cannot be selected
is not a node id.

## Question

`per-block` is a shipped CLI option with an ini twin and its own how-to sections.
How does it get retired without breaking a user who set it?

## Direction

Announce it as a breaking change with the migration path stated plainly, and keep
the option accepting `per-block` for one minor release, mapped to `merged` with a
{class}`pytest.PytestDeprecationWarning`.

Before landing, confirm no downstream consumer sets it.
`--doctest-docutils-modules` and `--no-doctest-docutils-modules` keep their exact
current spelling and `dest`, because downstream projects carry them in `addopts`.

## Open

- Whether the deprecation shim warns once per session or once per page.
- Whether `--doctest-docutils-namespace-scope` is renamed to `--doctest-docutils-share`
  in the same release or a later one. {doc}`0001-typed-vanilla-doctest-core`
  decides the vocabulary — `scope` is reserved for pytest's fixture-lifetime
  ladder — but the rename is independently schedulable.
- Whether the `pytest11` entry point rename (from `sphinx`, which is what
  `-p no:sphinx` disables today) ships in the same release as this removal or its
  own.
