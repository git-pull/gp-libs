# `sphinx.ext.doctest`

Pinned at [`v9.1.0`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py).

## Classification

A semantic fork. It invents its own document-level model — groups, phases, five
directives — and then converts all of it back into stdlib `doctest.DocTest`
objects for execution. It is the source of every author-facing spelling this
project supports, and the reason those spellings must be honoured exactly.

It is also builder-coupled: nothing in the pipeline is callable without a built
Sphinx app, and it produces no machine-readable results at all.

## Core data structures

```text
TestCode      code, type, filename, lineno, options            [:235]
              `type` in {testsetup, testcleanup, doctest, testcode, testoutput}
TestGroup     name, setup: list, tests: list, cleanup: list    [:200]
              add_code(code, prepend=False)                    [:207]
DocTestBuilder(Builder)                                        [:292]
              self.type: "single" | "exec"   <- mutable, read by a
                                                process-global compile patch
SphinxDocTestRunner(doctest.DocTestRunner)                     [:257]
```

`TestGroup.tests` holds heterogeneous entries — `[code]` for a bare block,
`[code, output]` for a paired testcode/testoutput. `add_code` is where three
silent losses live: an orphan `testoutput` is discarded, a second `testoutput`
*replaces* the first, and a `testcode`'s own options are dropped in favour of its
output block's.

## Data flow

```text
directive run()                                                [:66]
   |  parse group names from the optional argument
   |  trim `# doctest:` flags out of the RENDERED code, keep the original
   |    in node["test"]
   |  nodetype = nodes.comment  when name in {testsetup, testcleanup}
   |                            or "hide" in options            [:92-93]
   |  stamp node["testnodetype"], ["groups"], ["options"], ["skipif"]
   v
doctree
   |
DocTestBuilder.test_doc(docname, doctree)                      [:428]
   |  for node in doctree.findall(condition):
   |      if self.skipped(node): continue    <- GATED BLOCK IS DROPPED  [:443-444]
   |      code = TestCode(...)
   |      "*" in groups -> add to every group
   |      else groups[name].add_code(code)
   v
per group: ns = {}
   |  three runners: setup / test / cleanup, sharing one _fakeout
   |  test.globs = ns  (assigned AFTER construction)
   |  runner.run(test, out=..., clear_globs=False)
   |  self.type flipped to "exec" for setup, cleanup, testcode   [:548, :608]
   |                     to "single" for ordinary doctests       [:580]
   v
six integer counters + text streamed to outdir/output.txt
```

## Extension seams

| Seam | Kind |
|---|---|
| `TestDirective` subclassing, with `option_spec` ([`:66`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L66)) | subclass |
| The node attribute stamp — `testnodetype`, `groups`, `options`, `skipif`, `test` | implicit protocol |
| `doctest_global_setup`, `doctest_global_cleanup`, `doctest_test_doctest_blocks`, `doctest_default_flags` | Sphinx confvals |
| `is_allowed_version(spec, version)` ([`:45`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L45)) | function |

The node attribute stamp is the important one, and it is undocumented. It is the
only decoupled interface in the module: any directive that emits a
`literal_block` or `comment` carrying `testnodetype` participates. It is also
what makes a *third-party* collector — this project's — able to read a page
Sphinx's own directives produced, and vice versa. Reading attributes off the node
rather than trusting one's own directive classes is the only defence against
`Sphinx.add_directive` overriding a registration unconditionally.

## Semantics this project must match exactly

| Rule | Anchor |
|---|---|
| `testsetup`, `testcleanup` and `:hide:` render as `nodes.comment` | [`:92-93`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L92-L93) |
| `:options:` is accepted only on `doctest` and `testoutput` | [`:111`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L111) |
| A gated block is dropped during collection — no outcome, id or count | [`:443-444`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L443-L444) |
| `*` means every group the document declares; `default` means no argument was given | [`:428`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L428) onward |
| Setup runs before tests, cleanup after, whatever order the page writes them | `TestGroup` [`:200-226`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L200-L226) |
| `is_allowed_version` takes the **specifier first** | [`:45`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L45) |
| `doctest.compile` is rebound process-wide and never restored | [`:310`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L310) |

The last two are where this project deliberately diverges. The argument order was
a real defect in the local helper. The `compile` rebinding is unavailable to a
library that loads into every pytest session, which is the entire origin of
ADR 0001's decision to own the per-example loop instead.

The gated-block rule is the one semantic this project rejects on purpose: Sphinx's
drop destroys the node id, the count and the `-rs` line, and pytest users
reasonably expect a `SKIPPED` outcome with a reason.

## What it cannot do

- **Run outside a Sphinx build.** `DocTestBuilder` binds an `env`, a `config`, an
  `outdir`, a `sys.path` mutation and an open file handle.
- **Produce results a caller can inspect.** Six ints and text to a file. No failure
  can be mapped back to its node without re-parsing prose.
- **Distinguish two blocks in one group.** Every block in a group shares
  `DocTest.name`, which is why `SphinxDocTestRunner` overrides a private stdlib
  method to swallow the resulting `IndexError`
  ([`:257`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L257)).

## Anchors

- [`is_allowed_version`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L45) ·
  [`TestDirective`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L66) ·
  [`comment nodetype rule`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L92-L93)
- [`TestGroup`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L200) ·
  [`add_code`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L207) ·
  [`TestCode`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L235)
- [`SphinxDocTestRunner`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L257) ·
  [`DocTestBuilder`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L292) ·
  [`doctest.compile` patch](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L310)
- [`test_doc`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L428) ·
  [`skipped-node drop`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L443-L444) ·
  [`type = "exec"` for testcode](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L548)
- [User-facing contract](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/doc/usage/extensions/doctest.rst)
