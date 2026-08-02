# Prior art: Sybil, xdoctest, pytest-examples, typeshed

Four projects that solved some part of this problem differently. Each is read for
one specific question, and each answers it — two of them by counterexample.

---

## Sybil

Pinned at [`10.0.1`](https://github.com/simplistix/sybil/tree/10.0.1).

**The bet:** a document is a flat sequence of non-overlapping character spans, not
a parse tree, and everything else — markup format, language, assertion semantics,
test runner — is a plugin over that primitive. It parses nothing itself: no
docutils, no myst-parser, no CommonMark implementation, and zero runtime
dependencies. Every format is a regex `Lexer` producing `Region(start, end,
lexemes)` spans over raw text.

**Data model.** `Region` is a half-open span with three payload slots — `lexemes`,
`parsed`, `evaluator` — and lives in two undocumented-by-type states: lexed
(lexemes only) and parsed (evaluator attached). `Document` is text plus path plus
regions plus **one `namespace: dict`**. `Example` joins document and region at run
time and holds a *reference* to that namespace. `Sybil` itself is pure
configuration.

**What is genuinely good.** `Document.add` bisect-inserts and **raises
`ValueError` on any overlap**. That single invariant gives a total order for free
and converts the silent class of parser bug — a block dropped or collected twice —
into a loud error at collection time. It is the best structural decision in the
codebase.

Its public testing helpers (`check_lexer`, `check_parser`, `check_sybil`) are
documented *and* used by the project's own runnable documentation, so the
extension guide is under test. That is rare and worth copying.

**The fatal flaw.** One mutable namespace per document, and
[one independently selectable pytest item per region](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/integration/pytest.py).
`pytest -k` on an example whose predecessor bound a name raises `NameError`. The
documentation never mentions this; there is no discussion of `xdist`, parallelism
or deselection anywhere in it. This is axis 1 of
[`00-taxonomy.md`](00-taxonomy.md), in the unacknowledged column.

**The second flaw.** [Node ids are positional](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/sybil.py#L155-L157) —
`line:{line},column:{column}`. Adding a paragraph above an example renames every
downstream test, breaking `--lf`, `--nf`, deselect files, xfail lists and CI flake
history. For a *documentation* test runner, prose above examples is the thing that
changes most often.

**What it cannot do.** Groups. A regex cannot see a directive's options, so Sybil
has no group concept at all and directs users to clear the namespace instead. This
is the clearest available argument for paying the docutils dependency: if
`:skipif:`, `:options:` and group names are part of the product, the document
model has to be a parse tree.

**Verdict on the invariant.** The non-overlap check does not survive contact with
docutils: two `.. include::` directives naming the same file legitimately produce
blocks over identical source spans. Adopt the *idea* — detect double collection —
as a diagnostic carrying both provenances, not as an exception.

---

## xdoctest

Pinned at [`v1.3.2`](https://github.com/Erotemic/xdoctest/tree/v1.3.2).

**The bet:** a doctest is Python source that happens to live in a docstring, so
parse it with `ast`/`tokenize` rather than a line regex, and abandon stdlib
compatibility to fix the design.

**What is genuinely good.**

- `ast`-based parsing really is better than `_EXAMPLE_RE` for Python.
- Directives are **structured objects** rather than an int bitmask, and
  [`REQUIRES`](https://github.com/Erotemic/xdoctest/blob/v1.3.2/src/xdoctest/directive.py#L58)
  carries a *set of unmet requirements* — so a skip knows it skipped because
  `module:torch` was absent. A bool discards exactly the information the reader
  wants, and this is the single most transferable idea in the survey.
- Per-part synthetic filenames plus a filename-to-block map, so an exception raised
  inside a function that an *earlier* block defined is attributed to the defining
  block. Directly applicable to grouped namespaces.

**The counterexample it provides.** It is now building stdlib compatibility back,
in modules that did not exist at the tagged release. Getting stdlib semantics out
of its own intake seam requires setting `REQUIRE_WANT`,
`deferred_output_matching=False` **and** `compile_mode='single'` — three knobs to
undo one abandoned default, paid years later. This is the empirical answer to
"should the core be vanilla?"

**Two things not to copy.** Its got/want defaults are permissive —
`ELLIPSIS`, `NORMALIZE_WHITESPACE` and `NORMALIZE_REPR` all default true — which
silently changes the meaning of tests users wrote for stdlib. And unknown
directives and parse errors `warnings.warn` and vanish, so a typo weakens a test
instead of failing it. A test that reports green while checking nothing is worse
than no test.

It also unregisters pytest's doctest plugin outright, which is hostile in a
`pytest11` package.

---

## pytest-examples

Pinned at [`v0.0.18`](https://github.com/pydantic/pytest-examples/tree/v0.0.18).

**The bet:** invert the contract — the author does not write expected output, the
runner writes it. A block is a module exec'd once with `print` captured, and the
output is rendered back into the source file.

**What is genuinely good.**

- **Emitting the canonical form instead of parsing it collapses check-mode and
  update-mode into one code path.** That is a real structural insight.
- **Absolute byte offsets plus an invertible dedent scalar** are exactly what a
  data model needs to rewrite source. Read-only tools discard the indent; keeping
  it is the difference between "we could add `--update-examples` later" and "we
  would have to redesign the data model first". Two int fields.
- **It composes with pytest by contributing no collector at all.** Examples are
  `parametrize` params, so marks, `-k`, fixtures and xfail all work unmodified.
  This is the cheapest correct integration in the entire survey.

**What not to copy.** It hard-codes a stack depth as a magic integer — the depth of
another library's internal call stack — and forges frames through
`ctypes.pythonapi.PyFrame_New`. Its write-back splices at collection-time offsets
with no staleness check, so editing a file while it runs corrupts the file. And
its update mode is a session-scoped in-process two-phase commit, so `-x` or a crash
writes nothing and says nothing — the worst outcome for a tool whose selling point
is rewriting your files.

**Rule extracted.** Any write-back must content-hash the region at collection and
refuse on mismatch. An unconditional splice at stale offsets is data loss, not a
race.

---

## typeshed

Pinned at [`8c7256c`](https://github.com/python/typeshed/blob/8c7256c/stdlib/doctest.pyi)
(no tags on this repository; commit reachable from trunk).

**Read for:** what a typed `doctest` actually costs, and where the type system
gives up.

The stub annotates every public name and then hands back `Any` at exactly the
three extensible points: `globs: dict[str, Any]` (correct for values, since they
are user objects), `**options: Any` on the three suite builders (incorrect — the
accepted keys are exactly known), and `optionflags: int` everywhere (so
`optionflags=4096` type-checks).

Two facts matter for anything claiming to be a "typed vanilla core":

**The de-facto contract is the stub, not the source.** Downstream projects run
mypy against it. Narrowing `parse()` to `list[Example]`, dropping the `bool`
overload on `find`, or typing `out` as `Callable[[str], None]` stops type-checking
for existing typed callers whose code runs fine.

**Its largest consumer violates it deliberately.** `_pytest.doctest` repurposes
`out` from a write-callable into a *list*, with a `# type: ignore[arg-type]`. Any
honest typing of that parameter has to accommodate the ecosystem's actual usage.

The stub also has a false negative worth knowing: `DocTestRunner.test: DocTest` is
declared unconditionally, while runtime assigns it only inside `run()`. A stub that
type-checks a crash is worse than no stub for that attribute.

**Rule extracted.** Keep the runtime objects structurally identical to stdlib's and
put precision in a parallel layer — `TypedDict` over the node-attribute channel,
`Protocol`s for the seams, `Literal` for closed vocabularies. Do not narrow a
signature typeshed publishes wider.
