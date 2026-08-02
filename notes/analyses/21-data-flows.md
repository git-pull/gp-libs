# Cross-cutting: the data flows, lined up

Four pipelines that all end in the same `exec()`, drawn to the same scale so the
divergence points are visible.

## The pipelines

```text
CPython doctest
  string ─► DocTestParser.parse ─► DocTestFinder.find ─► DocTestRunner.run
                                                            └─► __run ─► exec

pytest --doctest-glob
  path ─► pytest_collect_file ─► DoctestTextfile.collect ─► DoctestItem
            (one DocTest for the whole file)                    ├─ setup():   globs.update(fixtures)
                                                                ├─ runtest(): runner.run(clear_globs=True)
                                                                └─ repr_failure(): per-failure location

sphinx.ext.doctest
  doctree ─► test_doc ─► condition filter ─► skipped? DROP
                             │
                             ├─► TestCode ─► TestGroup{setup, tests, cleanup}
                             │
                             └─► per group: ns={}; test.globs=ns (post-construction)
                                  3 runners (setup/test/cleanup), clear_globs=False
                                  self.type flipped single/exec around each run
                                     └─► doctest.compile (PROCESS-GLOBAL PATCH) ─► exec

ADR 0001
  path ─► markup.parse_file ─► (Blocks, Diagnostics)
                                   │
                                   ├─► project() ─► GroupPlan{group, blocks[], seed}
                                   │     pure: no docutils, no pytest, no filesystem,
                                   │     no user code — :skipif: passes through unevaluated
                                   │
                                   └─► Document(pytest.Module) ─► DocutilsItem (one per GROUP)
                                          ├─ setup():   globs cleared, then fixtures injected
                                          ├─ runtest(): run_group() runs each block's DocTest
                                          │             in phase order, clear_globs=False
                                          │             :skipif: evaluated HERE
                                          │             DocutilsRunner.__run ─► exec (mode from data)
                                          └─ repr_failure(): inherited; reads each block's own DocTest
```

## Where they diverge

**At the gate.** Sphinx evaluates `:skipif:` during collection and *drops* the
node. pytest cannot express that — an item must exist to have an outcome — so
`doctest_docutils` marks the block `SKIP` instead. ADR 0001 moves the evaluation
to `runtest()`, which additionally buys collection purity: with no user code
running at collection, worker collections cannot diverge and `--collect-only`
cannot have side effects.

**At the globs assignment.** Every system that shares state has to assign
`test.globs` *after* `DocTest.__init__`, because the constructor
[copies](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565).
Sphinx does this explicitly. pytest does not share at all, and its
[`runtest`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L295-L303)
runs with `clear_globs` defaulting to `True` — so any design that inherits
`runtest()` unchanged and expects sharing gets its mapping emptied after the first
block. That is a trap with no diagnostic; the symptom is a `NameError` in block
two.

**At the compile call.** stdlib hard-codes `"single"`. Sphinx flips a mutable
builder attribute and reads it through a process-global rebinding of
`doctest.compile` that is never restored. PR #87 proposes cloning the
mangled loop's code object to get a private version of that rebinding. ADR 0001 puts the policy on the projected *block*, materializes a runtime per
profile, and reads it in a loop it owns — and only for extended profiles, since
ordinary prompt blocks run on CPython's untouched loop — the only one
of the four that neither mutates process state nor copies a code object.

**At the location.** stdlib computes `test.lineno + example.lineno + 1`. Sphinx
gives every block in a group the same `DocTest.name` and pays for it by overriding
a private method to swallow an `IndexError`. PR #87 fabricates a
synthetic page so the arithmetic stays true across merged blocks. ADR 0001 gives
each block its own `DocTest`, so the arithmetic is true without fabrication.

## The order-of-operations facts

Three orderings are load-bearing and each has a failure mode with no error
message.

**Fixtures are injected in `setup()`, into the mapping, in place.**
`DoctestItem.setup()` does `self.dtest.globs.update(globs)`
([`:288-293`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L288-L293)).
A design that clears and rebinds the mapping around that call either discards the
injected names — so `getfixture` raises `NameError` — or reuses the previous
attempt's mutations. Under `--reruns`, the second is a false green: an expectation
true only on attempt two reports as a pass.

**Phase order and page order are different orders.** A group hands its blocks over
as setup, tests, cleanup; a reader meets them in whatever order the page writes
them. Any layout that anchors reported lines on the *run* order reports examples
against whichever block came first in that sequence — and can point past the end of
the file. Sphinx sidesteps this by not reporting useful lines at all.

**Collection order must be numeric, never lexicographic.** `DocTest.__lt__`
compares names as text
([`:596`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596)),
and names carry positions as text, so any accidental `sorted()` runs `page.md[10]`
before `page.md[1]`. Every test still passes, in the wrong sequence — and for a
group sharing state, the wrong sequence is the bug.

## Anchors

- [`DocTest.__init__` globs copy](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) ·
  [`__lt__`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596) ·
  [`__run`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344) ·
  [`compile(..., "single", ...)`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1400)
- [`DoctestItem.setup`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L288-L293) ·
  [`runtest`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L295-L303)
- [`test_doc`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L428) ·
  [gated-node drop](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L449-L450) ·
  [`doctest.compile` patch](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L310)
