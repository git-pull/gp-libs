# Taxonomy: the axes a doctest engine is classified on

Nine axes. Every system in these notes takes a position on each, and most of the
disagreements between them reduce to a different position on one axis rather than
a different philosophy.

## The axes

| # | Axis | Positions |
|---|---|---|
| 1 | **Sharing unit vs. selection unit** | same object · different objects, acknowledged · different objects, unacknowledged |
| 2 | **Test identity** | author-declared name · symbol-derived · positional (line/column or byte range) |
| 3 | **Runtime object model** | stdlib `DocTest`/`Example` · own model with a bridge · own model, no bridge |
| 4 | **Document model** | real parse tree · flat character spans · regex over text · none |
| 5 | **Option representation** | `int` bitmask · structured state · enum |
| 6 | **Extension mechanism** | callable aliases · nominal subclassing · named registry · `Protocol` · none |
| 7 | **Relationship to pytest's doctest plugin** | compose · block/unregister · replace by instruction · no collector |
| 8 | **Got/want strictness** | stdlib defaults · permissive defaults · no want at all |
| 9 | **Direction of data** | read-only · read plus write-back |

## Where each system sits

| System | 1 sharing/selection | 2 identity | 3 object model | 4 document model |
|---|---|---|---|---|
| CPython `doctest` | same (one `DocTest` per docstring) | dotted symbol path | *is* the model | none — line regex over a string |
| `_pytest.doctest` | same (one item per `DocTest`) | `path::module.qualname` | stdlib, unchanged | none — delegates |
| `sphinx.ext.doctest` | same (one group, one runner pass) | group name, shared by every block | stdlib, constructed per group | real doctree |
| Sybil | **different, unacknowledged** | positional `line:N,column:N` | stdlib `Example`, one-line `DocTest` fork | flat character spans |
| xdoctest | same (one `DocTest` per docstring) | `Callname:N` | own, with a late bridge back | none for `.rst`/`.txt` |
| pytest-examples | none — no implicit sharing | positional `path:start-end` | none | regex over fences |
| `doctest_docutils` today | configurable; `per-block` is different-and-guarded | group name, or `page.md[k]` | stdlib | real doctree |
| ADR 0001 | **different, decoupled by construction** | group name, or `page.md[k]` | stdlib | real doctree |

| System | 5 options | 6 extension | 7 vs. pytest doctest | 8 strictness | 9 direction |
|---|---|---|---|---|---|
| CPython `doctest` | `int` bitmask + registry | nominal subclassing | n/a | strict | read-only |
| `_pytest.doctest` | `int` + name lookup | subclass its classes | *is* it | strict | read-only |
| `sphinx.ext.doctest` | `int` via `:options:` | directive subclassing | unaware | strict | read-only |
| Sybil | `int` | callable aliases | replace by instruction (`-p no:doctest`) | strict | read-only |
| xdoctest | structured `TypedDict` + bridge | two registries, else fork | unregisters it | **permissive** | read-only |
| pytest-examples | n/a | none | no collector — composes trivially | no want at all | **write-back** |
| `doctest_docutils` today | `int` + a forked lookup | directive subclassing | blocks it, imports its privates | strict | read-only |
| ADR 0001 | `int` + registry | `Protocol` + nominal + `BlockKind` registry | **compose; require it** | strict | read-only |

## What the matrix shows

**Axis 1 is the only one where a wrong answer is silent.** Every other axis
produces inconvenience — a renamed test, a conversion layer, an extra knob. Axis 1
produces a `NameError` in a test the user believed they could select, or a false
green under `--reruns`. Sybil sits in the unacknowledged column and its
documentation never mentions it.

**Axes 1 and 2 are independent, and everyone treated them as one.** The full
product space is four cells:

|  | one node id | N node ids |
|---|---|---|
| **one `DocTest`** | Sphinx, `doctest_docutils` `merged` | — (incoherent) |
| **N `DocTest`s** | *unoccupied until ADR 0001* | Sybil, `doctest_docutils` `per-block` |

The bottom-right cell is where the silent failure lives. The bottom-left cell —
per-block `DocTest`s under one item — gives per-block reporting *and* an
unsplittable sharing unit, and no surveyed project occupies it.

**Axis 3 has an empirical answer.** xdoctest is the controlled experiment for
abandoning the stdlib object model, and it is now building the bridge back. The
cost of divergence is paid years later, in knobs that exist only to restore the
default that was abandoned.

**Axis 4 is decided by axis 6.** A regex cannot see `:skipif:` or a group name,
which is why Sybil has no group concept at all and tells users to clear the
namespace instead. If directive options are part of the product, the document
model must be a parse tree.

**Axis 7 correlates with hostility.** Two of the surveyed projects disable
pytest's doctest plugin — one in `pytest_configure`, one by telling users to pass
`-p no:doctest`. A `pytest11` plugin loads into sessions belonging to people who
never asked for it, and the plugin it disables is the one whose checker, failure
repr and `doctest_namespace` fixture it wants to keep.
