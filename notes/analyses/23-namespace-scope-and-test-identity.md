# Cross-cutting: namespace scope and test identity

The one axis where a wrong answer is silent. Every other design choice in these
notes produces inconvenience — a renamed test, a conversion layer, an extra knob.
This one produces a `NameError` in a test the user believed they could select, or a
green run that should have been red.

## The two questions, which are not the same question

1. **Which blocks share a `globs` mapping?** (scope)
2. **Which blocks can be selected, reported and scheduled independently?**
   (identity)

Everything downstream — `-k`, `--lf`, `--deselect`, `-x`, `--reruns`, every
`--dist` mode, JUnit rows, flake history — depends on the second. Everything a
narrative page needs depends on the first.

## The product space

|  | one node id | N node ids |
|---|---|---|
| **one `DocTest`** | `sphinx.ext.doctest`; `doctest_docutils` `merged` | incoherent |
| **N `DocTest`s** | *unoccupied until ADR 0001* | Sybil; `doctest_docutils` `per-block` |

The bottom-right cell is where the silent failure lives, and two shipped projects
are in it.

Sybil is there **unacknowledged**: one `Document.namespace` shared by reference,
one pytest item per region. `pytest -k` on an example whose predecessor bound a
name raises `NameError`, and nothing in its documentation says so.

`doctest_docutils`'s `per-block` mode is there **acknowledged and guarded** — the
guards are the xdist scheduler substitution, the scheduler refusal, and the
run-twice refusal. Those guards are the reason `_worker_count`, `_shared_page`,
`_is_page` and `_splitting_scheduler` exist at all.

The bottom-left cell gives per-block reporting *and* an unsplittable sharing unit,
and it needs no guards, because there is nothing to split.

## Why the guards are expensive

The constraints come from [`12-pytest-xdist.md`](12-pytest-xdist.md) and are all
structural, not incidental:

- A live mapping is a Python object; only execnet-serializable builtins cross a
  worker boundary.
- The controller never collects, so it cannot ask "which items share state" — it
  sees node-id strings and nothing else. Any protection must be *inferred from
  string shape* or *encoded into the id*.
- The only affinity primitive is
  [`_split_scope(nodeid) -> str`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284).
  `load` and `worksteal` have no scope concept at any layer, so under a user-typed
  `--dist load` the options are refuse, substitute, or do not need protecting.
- `xdist_group` is applied
  [worker-side](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254)
  and only when the worker's own `--dist` is literally `loadgroup`. A
  controller-side substitution never reaches a worker.
- A worker crash re-runs only the *uncompleted* items of a work unit, on a fresh
  process. Blocks 3..N then run against an empty mapping. Restarts are on by
  default.
- A retry (`--reruns`, `--count`) re-runs a block against globals it already
  mutated, so an expectation true only on attempt two reports **PASS**.

Every one of these evaporates when the item is the sharing unit.

## Test identity: never positional

Two of the surveyed projects derive node ids from position — Sybil's
[`line:{line},column:{column}`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/sybil.py#L155-L157)
and pytest-examples' `path:start-end`.

For a *documentation* test runner this is indefensible, because prose above
examples is the thing that changes most often. Adding a sentence renames every
downstream test, which breaks `--lf`, `--nf`, checked-in deselect files, xfail
lists and CI flake history. pytest-examples compounds it: the same string is the
dedupe key for its write-back, so an identity collision becomes file corruption.

The rule: **author-declared name first, stable ordinal as fallback, and the
fallback shape invariant across configuration.** The test to apply is concrete —
adding a sentence to a page must rename zero tests.

Two corollaries:

- `DocTest.name` must be machine-independent. Embedding an absolute path makes a
  checked-in `--deselect` resolve only on the machine that produced it, and puts a
  home directory in JUnit XML.
- Column is not worth carrying. It adds churn and disambiguates nothing once names
  exist.

## What a node id does *not* promise

Worth stating plainly, because it is the honest limit of the recommended design:
**no surveyed implementation makes a node id a promise of independent
runnability.** Selecting block two of a stateful page raises `NameError` under
Sybil, under `per-block`, and under any scheme that hands out per-block ids over
shared state.

The choice is therefore not between "selectable blocks" and "unselectable blocks".
It is between an id that *claims* to be selectable and is not, and an id whose
granularity honestly matches what can be run alone. `merged` and ADR 0001 both
choose the latter; they differ only in whether the reporting granularity has to
match the selection granularity, and ADR 0001's answer is that it does not.

## Fixture lifetime falls out of this

A page collected as a `pytest.Module` **is** the module scope, so
`@pytest.fixture(scope="module")` already has page lifetime — no shim required.
Sybil reaches the same outcome through a `getparent` override that returns the
file collector when pytest asks for `Module`.

The corollary is a trap for any design that shares state across items without
sharing the item: fixtures do not follow. A block that stashes a fixture-derived
object under a name keeps answering after that fixture has been finalized, because
the name outlives the object's lifetime. Making the item the sharing unit aligns
the two — the mapping and the fixtures have the same lifetime because they have the
same owner.

## Anchors

- [`DocTest.__init__` globs copy](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565)
- [`runtest` with `clear_globs=True`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L295-L303) ·
  [`setup` globs update](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L288-L293)
- [`_split_scope`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284) ·
  [`xdist_group` append](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254) ·
  [collection-mismatch abort](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py#L259)
- [Sybil `identify`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/sybil.py#L155-L157) ·
  [Sybil pytest integration](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/integration/pytest.py)
