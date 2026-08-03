# `sphinx.ext.doctest`

Pinned at [`v8.2.3`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py),
the version this project resolves. Sphinx 9.0 changed only the fallback for a
bare doctest node with no `groups` attribute: it now uses
`doctest_test_doctest_blocks`
([`v9.0.0:463`](https://github.com/sphinx-doc/sphinx/blob/v9.0.0/sphinx/ext/doctest.py#L463)).
An unargumented Sphinx directive still stamps `groups=["default"]`
([`v9.0.0:94-98`](https://github.com/sphinx-doc/sphinx/blob/v9.0.0/sphinx/ext/doctest.py#L94-L98)),
so its group did not change.

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
`[code, output]` for a paired testcode/testoutput. `add_code` is where the silent
losses live: an orphan `testoutput` is discarded; a `testoutput` following a
`doctest` block is discarded, because a doctest entry has length 1 and fails the
`len(latest_test) == 2` guard; and a second `testoutput` *replaces* the first.

A fourth silent loss is in the directives rather than `add_code`: `:pyversion:` is
declared on **both** `testcode`
([`:174-180`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L174-L180))
and `testoutput`
([`:184-190`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L184-L190)),
and honoured on neither — the version gate runs only for `doctest`. An author who
writes it on either gets no error and no gate.

`:options:` on a `testcode` is **not** a silent loss. It is absent from
`TestcodeDirective.option_spec` entirely, so writing it is an unknown-option
error that drops the block — loud, and visible in the build output.

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
   |      if self.skipped(node): continue    <- GATED BLOCK IS DROPPED  [:449-450]
   |      code = TestCode(...)
   |      "*" in groups -> add to every group
   |      else groups[name].add_code(code)
   v
per group: ns = {}
   |  setup codes -> ONE simulated DocTest containing N Examples
   |  each ordinary or paired test -> ONE DocTest
   |  cleanup codes -> ONE simulated DocTest containing N Examples
   |  all have test.globs = ns after construction, since __init__ copies
   |  runner.run(test, out=..., clear_globs=False)
   |  self.type flipped to "exec" for setup, cleanup, testcode   [:549, :608]
   |                     to "single" for ordinary doctests       [:580]
   |
   |  if setup fails -> RETURN. Cleanup does not run.            [:554-556]
   v
six builder counters + text streamed to outdir/output.txt
```

## Extension seams

| Seam | Kind |
|---|---|
| `TestDirective` subclassing, with `option_spec` ([`:66`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L66)) | subclass |
| The node attribute stamp — `testnodetype`, `groups`, `options`, `skipif`, `test` | implicit protocol |
| `doctest_global_setup`, `doctest_global_cleanup`, `doctest_test_doctest_blocks`, `doctest_default_flags` | Sphinx confvals |
| `is_allowed_version(spec, version)` ([`:45`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L45)) | function |

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
| `testsetup`, `testcleanup` and `:hide:` render as `nodes.comment` | [`:92-93`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L92-L93) |
| `:options:` is accepted only on `doctest` and `testoutput`; on a `testcode` it is an unknown-option error, not a discard | [`:111`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L111), [`:174-180`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L174-L180) |
| Cleanup does **not** run when setup fails — the group returns early | [`:554-556`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L554-L556) |
| A gated block is dropped during collection — no outcome, id or count | [`:449-450`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L449-L450) |
| `*` means every group the document declares; an unargumented directive stamps `default` | [`:94-98`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L94-L98), [`:428`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L428) onward |
| Setup runs before tests, cleanup after, whatever order the page writes them | `TestGroup` [`:200-226`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L200-L226) |
| `is_allowed_version` takes the **specifier first** | [`:45`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L45) |
| `doctest.compile` is rebound process-wide and never restored | [`:310`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L310) |

The last two are where this project deliberately diverges. The argument order was
a real defect in the local helper. The `compile` rebinding is unavailable to a
library that loads into every pytest session, which is the entire origin of
ADR 0001's decision to own the per-example loop instead.

Two more are rejected on purpose. Sphinx's gated-block drop destroys the node id,
the count and the `-rs` line, where pytest users reasonably expect a `SKIPPED`
outcome with a reason. And the setup-failure short-circuit leaves a page's
`testcleanup` unrun, which for a page that spawns a server in setup means a leak.

**One thing Sphinx already does that is worth stating plainly:** it runs one
`DocTest` *per block* against one shared group namespace. That execution shape is
not novel to ADR 0001. What Sphinx lacks is any selectable, reportable identity
for those blocks — they all share one `DocTest.name`, which is the defect below.

## What it cannot do

- **Run outside a Sphinx build.** `DocTestBuilder` binds an `env`, a `config`, an
  `outdir`, a `sys.path` mutation and an open file handle.
- **Produce results a caller can inspect.** Six ints and text to a file. No failure
  can be mapped back to its node without re-parsing prose.
- **Distinguish two blocks in one group.** Every block in a group shares
  `DocTest.name`, which is why `SphinxDocTestRunner` overrides a private stdlib
  method to swallow the resulting `IndexError`
  ([`:257`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L257)).

## Anchors

- [`is_allowed_version`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L45) ·
  [`TestDirective`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L66) ·
  [`comment nodetype rule`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L92-L93)
- [`TestGroup`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L200) ·
  [`add_code`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L207) ·
  [`TestCode`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L235)
- [`SphinxDocTestRunner`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L257) ·
  [`DocTestBuilder`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L292) ·
  [`doctest.compile` patch](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L310)
- [`test_doc`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L428) ·
  [`skipped-node drop`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L449-L450) ·
  [`type = "exec"` for testcode](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L548)
- [User-facing contract](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/doc/usage/extensions/doctest.rst)
