# Cross-cutting: the data structures, lined up

Every system in these notes ends up representing the same four things: a *unit of
source*, a *unit of execution*, a *unit of shared state*, and a *unit of result*.
The disagreements are entirely about which of those four are the same object.

## The four units

| System | source unit | execution unit | shared-state unit | result unit |
|---|---|---|---|---|
| CPython `doctest` | `Example` | `DocTest` | `DocTest.globs` | `TestResults` (2 ints + an attribute) |
| `_pytest.doctest` | `Example` | `DocTest` = one `Item` | `DocTest.globs`, wiped per item | `MultipleDoctestFailures` → `ReprFailDoctest` |
| `sphinx.ext.doctest` | `TestCode` | one `DocTest` **per block** (`TestGroup` is the batching unit, not the execution unit) | `ns`, assigned post-construction to every block's `DocTest` | six ints + text to a file |
| Sybil | `Region` | `Example` = one `Item` | `Document.namespace` | truthy return or exception |
| xdoctest | `DoctestPart` | own `DocTest` | `global_namespace` | own report objects |
| pytest-examples | `CodeExample` | the block, exec'd once | explicit `module_globals=` | captured output, or a rewrite |
| ADR 0001 | `Block` | `DocTest` per block | one `globs` per **group**, on the `Item` | stdlib's, per block |

Reading across the "shared-state unit" column against the "execution unit" column
is the whole design problem. Sphinx and Sybil both put the shared state at a
coarser granularity than the execution unit. Sphinx gets away with it by having
no selectable unit at all — it is a builder, not a test runner, so there is
nothing for a `-k` to split. Sybil does not: it hands out one pytest item per
span over one shared mapping, which is the failure.

Three units are easy to conflate for Sphinx specifically, so keep them apart: the
**runner call** is per block, the **shared state** is per group, and the **result**
is six process-wide integers.

## Field-by-field: what a source unit carries

| Field | `Example` | `TestCode` | `Region` | `CodeExample` | `Block` (ADR 0001) |
|---|---|---|---|---|---|
| source text | `source` | `code` | via `lexemes` | `source` | `source` |
| expected output | `want` | paired separately | — | written, not read | `want` |
| line | `lineno` (0-based, string-relative) | `lineno` | computed from span | `start_line` | `line` (nullable) |
| byte offsets | — | — | `start`, `end` | `start_index`, `end_index` | — (deferred) |
| dedent scalar | `indent` | — | `Lexeme.offset` | `indent` | — (deferred) |
| kind | — | `type` | inferred from evaluator | `prefix_tags()` | `kind` |
| group | — | via `TestGroup` | — | — | `groups` |
| options | `options` | `options` | — | — | `options` |
| gate | — | `skipif` on the node | — | — | `skipif` (unevaluated) |
| file | on the `DocTest` | `filename` | on the `Document` | `path` | `path` |
| compile mode | — | on the *builder*, mutable | — | always exec | on the `Example` subclass |

Three observations.

**Only pytest-examples carries byte offsets and an invertible dedent.** Those two
fields are the entire difference between a read-only tool and one that can rewrite
expected output later. ADR 0001 defers them, which is a decision to be revisited
rather than a decision made.

**Compile mode is on the wrong object everywhere except ADR 0001.** Sphinx keeps
it as mutable builder state read through a process-global patch; stdlib hard-codes
it in the loop. Putting it on the example data is what lets it survive
`copy.copy`, merging and any reordering, without a flag some runner has to be
holding at the right moment.

**Nobody but ADR 0001 makes the line nullable.** Every other system either always
has a line (because it computed the span itself) or fabricates one. With a real
doctree there are constructs that genuinely have no recoverable line, and pytest
has a branch for exactly that — `EXAMPLE LOCATION UNKNOWN` — which is unreachable
unless the model can express it.

## What a result unit carries

None of these systems produce a per-example result *value*:

- stdlib returns `TestResults(failed, attempted)` with `skipped` bolted on as an
  instance attribute, and pushes everything else through `out` as text.
- pytest works around that by repurposing `out` into a list so `report_*` can
  append, then rebuilds a location by slicing `test.docstring`.
- Sphinx works around it by not producing machine-readable results at all.

This absence is why a merged `DocTest` needs a synthetic page with blank-line
padding: the only channel for a location is `(test.lineno, test.docstring,
example.lineno)`, so a group holding many blocks must fabricate a docstring in
which those arithmetic relations still hold.

Giving each block its own `DocTest` removes the need for the fabrication rather
than improving it — the three fields are then already true.

## Anchors

- [`Example` / `DocTest` / `TestResults`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114)
- [`TestCode`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L235) ·
  [`TestGroup`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L200)
- [`MultipleDoctestFailures`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L172) ·
  [`repr_failure`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L317-L344)
- [Sybil `Region`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/region.py) ·
  [Sybil `Document`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/document.py)
