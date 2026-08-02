(adr-0001-typed-vanilla-doctest-core)=

# ADR 0001: A typed, vanilla-compatible doctest core

Status: Proposed
Date: 2026-08-02

## Context

`doctest_docutils` re-implements the *finding* half of {func}`doctest.testfile`
over a docutils or MyST doctree, keeps CPython's *running* half, and adds a
grouping layer — namespace, phase, merge, lift — that exists in neither parent.
`pytest_doctest_docutils` wraps that in a pytest plugin.

The two modules work. They are also the join point of three separate
vocabularies and three separate extension models, and the seams between them
were never named. Four structural costs follow.

**The finder is one method.** `DocutilsDocTestFinder._find` performs format
dispatch, node filtering, group resolution, wildcard expansion, name-collision
detection, `:skipif:` evaluation, `testoutput` pairing, test construction,
merging, splitting and naming, in one body with two nested closures, with
configuration threaded through as positional parameters. There is no boundary
between *document → blocks*, *blocks → tests*, and *tests → items*, so a change
to any one of them is a change to all three.

**It reaches through name-mangled CPython privates.** Sphinx's prompt-free
`{testcode}` form needs `compile()` in `"exec"` mode, but the per-example loop
[`DocTestRunner.__run`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344)
hard-codes `"single"`
([`Lib/doctest.py:1400`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1400)).
`sphinx.ext.doctest` solves this by rebinding `doctest.compile` process-wide and
never restoring it
([`sphinx/ext/doctest.py:310`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L310)) —
unavailable to a library that loads into every pytest session that installed it.
`_exec_mode_run` therefore clones the mangled method's code object into a fresh
{class}`types.FunctionType` whose globals map `compile` to a local helper, guarded
by probing `co_freevars` and `co_names` and degrading with a logged error. That
mechanism also carries a latent defect: its globals are a snapshot of
`vars(doctest)` taken at import, so a later rebind of a module-level name in
`doctest` is invisible to the clone while remaining visible to the stock runner,
and two runners in one process disagree.

**It blocks the plugin whose internals it imports.** `pytest_configure` calls
`config.pluginmanager.set_blocked("doctest")`, and the same module then imports
that plugin's private helpers — `_is_setup_py`, `_is_main_py`, `_get_checker`,
`_get_continue_on_failure` — and reads four ini and CLI options the blocked
plugin declared. This survives only because `_pytest/fixtures.py` has no
`pytest_plugin_unregistered` handler, so the already-parsed `doctest_namespace`
fixture outlives unregistration.

**It forks pytest-xdist to protect state xdist cannot see.** Because a live
`globs` mapping is a Python object and only execnet-serializable builtins cross a
worker boundary, a shared namespace must either be merged into one
{class}`doctest.DocTest` or kept on one worker. Keeping it there means a
scheduler, and the only affinity primitive in all of xdist is
[`LoadScopeScheduling._split_scope`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284),
a pure function on node-id strings. The controller never collects; it learns the
suite only as node ids arriving from workers. So `_shared_page` and `_is_page`
re-derive "these ids share state" from strings, and `_worker_count` re-implements
[`parse_tx_spec_config`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26)
including its quirks.

Underneath all four is one conflation. **The granularity of test identity and the
granularity of shared state are different axes, and the current design couples
them.** `namespace_items = merged` gives one `DocTest` and one node id per group;
`per-block` gives N `DocTest`s, N node ids, and one live mapping — a node id that
raises `NameError` when selected alone. Every surveyed project makes the same
mistake or a worse one (see [](#prior-art)).

## Decision

**The pytest item is the group. The {class}`doctest.DocTest` is the block.**

One {class}`pytest.Item` per (document, group). Inside it, a tuple of per-block
`DocTest`s run in phase order against one live `globs` mapping that never leaves
the item.

This occupies the cell no surveyed project occupies: N `DocTest`s, one node id.
Per-block failure locations, per-block gutters, per-block `SKIPPED`, per-block
"location unknown" — while `-k`, `--lf`, `-x`, `--reruns` and every `--dist` mode
are structurally incapable of splitting the shared state, because there is only
one item to schedule.

### The three facts this rests on

Each was verified by executing it, not by reading it.

**1. pytest reads failure locations per failure, not per item.**
[`DoctestItem.repr_failure`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L317)
iterates the failure list and reads `failure.test.filename`, `failure.test.lineno`
and `example.lineno` inside the loop
([`_pytest/doctest.py:337-344`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L337-L344)):

```python
for failure in failures:
    example = failure.example
    test = failure.test
    filename = test.filename
    if test.lineno is None:
        lineno = None
    else:
        lineno = test.lineno + example.lineno + 1
```

With one `DocTest` per block, every failure therefore carries its own `filename`
and `lineno` for free. A block reached through `.. include::` reports the
*included* file. A block docutils could not locate carries `lineno=None` and
takes pytest's honest `EXAMPLE LOCATION UNKNOWN` branch **without poisoning its
siblings**. No override of `repr_failure` or `reportinfo` is required.

This is what retires `_merge_blocks`: the synthetic merged page, its blank-line
padding and its `max(..., len(lines))` clamp exist only to reconstruct locations
from a single spliced docstring.

**2. `_DocTestRunner__run` is an ordinary attribute override.** Name mangling
rewrites the *call site* at compile time, so the `self.__run(...)` lookup inside
`run()`
([`Lib/doctest.py:1571`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1571))
resolves through the instance's MRO like any other attribute. A subclass that
defines `_DocTestRunner__run` takes over the loop, with `run()` untouched.

This page is itself a doctest, so the claim is checked on every run:

```{doctest}
>>> import doctest
>>> import io
>>> fired = []
>>> class Runner(doctest.DocTestRunner):
...     def _DocTestRunner__run(self, test, compileflags, out):
...         fired.append(test.name)
...         return super()._DocTestRunner__run(test, compileflags, out)
>>> example = doctest.Example("1 + 1\n", "2\n")
>>> test = doctest.DocTest([example], {}, "demo", "demo.py", 0, None)
>>> Runner().run(test, out=io.StringIO().write)
TestResults(failed=0, attempted=1)

The subclass method ran, and `run()` was never overridden:

>>> fired
['demo']
```

Keeping `run()` as stdlib's matters: it owns the save-and-restore of
`sys.stdout`, `pdb.set_trace`, `linecache.getlines`, `sys.displayhook`,
`_colorize.can_colorize` and the `PYTHON_COLORS`/`FORCE_COLOR` environment
variables, all in its own `finally`
([`Lib/doctest.py:1534-1573`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1534-L1573)).
That contract is not reproduced; it is inherited.

**3. Making the item the sharing unit dissolves distribution.** A live mapping
never crosses a process boundary, so there is nothing for xdist to split, under
any `--dist` mode. No affinity primitive, no scheduler substitution, no
`parse_tx_spec_config` fork, no node-id string sniffing.

### Layers

Dependencies flow one way, from the leaf toward the hosts. No layer may import a
layer above it.

```text
blocks              inert data: Block, BlockKind, Phase, Diagnostic, Example
   |                (stdlib imports only)
markup/             _rst, _myst, _text, _python -> (blocks, diagnostics)
   |
project             grouping, pairing, phase order, naming -> GroupTest
   |
runner              owns the per-example loop; phase sequencing
   |
settings            one frozen Settings, resolved once
   |
pytest_doctest_docutils   collection, items, globs lifetime, reporting
```

| Layer | Owns | Must not know |
|---|---|---|
| `blocks` | `Block`, `BlockKind` registry, `Phase`, `Diagnostic`, `BlockAttributes`, `Example(doctest.Example)` carrying compile mode | docutils, MyST, Sphinx, pytest, xdist, the filesystem. Stdlib imports only, enforced by an `import-linter` contract |
| `markup/` | Text → `(blocks, diagnostics)`. Line-number recovery and its per-front-end meaning, `.. include::` attribution, `nodes.comment` traversal, reporter capture, idempotent directive registration | Groups as a runtime concept, `DocTest`, pytest, pairing |
| `project` | The **only** place grouping exists: `*` expansion, anonymous naming, phase order, `testcode`/`testoutput` pairing, option defaults, name minting. A pure function | docutils, pytest, the filesystem, whether anything will run. Evaluates no user code |
| `runner` | `_DocTestRunner__run`; option merge, `SKIP`-after-merge, `FAIL_FAST`, `report_*` dispatch, version shims. `run_group()` owns phase sequencing and the `try`/`finally` guaranteeing `testcleanup` | docutils, markup, pytest. Never overrides `run()` |
| `settings` | One frozen `Settings` resolved once, with `None` sentinels at the resolve boundary so a future default change is announceable | pytest's `Config`, argparse, ini format, Sphinx's `app` |
| `pytest_doctest_docutils` | Options, `Document(pytest.Module)`, `DocutilsItem`, group `globs` lifetime, built-in-plugin dedup, surfacing diagnostics | docutils node classes, MyST configuration, grouping rules |

`pytest_doctest_docutils._compat` is the only module that imports
`_pytest.doctest`, behind a pinned support matrix. See
{doc}`0006-pytest-private-api-compatibility`.

### Vocabulary

Goal (e) — speaking doctest's, pytest's *and* Sphinx's idioms — is mostly a
naming problem, because the three overload the same nouns with different
referents. Each term below is decided once and used only that way.

| Term | doctest | pytest | Sphinx | Decision |
|---|---|---|---|---|
| `globs` | the dict examples exec in; [`DocTest.__init__` stores a **copy**](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) | — | assigned to `test.globs` after construction, run with `clear_globs=False` | Keep `globs` for the mapping |
| namespace | — | [`doctest_namespace`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L721) means *injected names* | — | **Not** used for the sharing unit; pytest owns the word |
| group | — | `xdist_group` is a *scheduling* affinity marker ([`remote.py:245-254`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254)) | the author-facing bucket: `.. doctest:: intro`, `default`, `*` | Adopt `group` for the sharing unit. The xdist affinity key is *derived*, never the group name |
| scope | — | the fixture-lifetime ladder | — | Reserved for pytest. The block-vs-document axis becomes `share` |
| test / item / block | `DocTest`, `Example` | `Item` | [`TestCode`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L235) is the parsed unit | Three nouns: `Example` (stdlib), `Block` (parsed), `DocTest` (runnable) |
| skip | the `SKIP` flag, short-circuiting before `report_start` | a reported outcome with a reason | [drops the node entirely](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L443-L444) | pytest's meaning, doctest's mechanism. Sphinx's drop is deliberately rejected |
| directive | inline `# doctest: +FLAG` | — | a docutils directive with an `option_spec` | Reserved for the docutils meaning. doctest's form is "inline flags" |
| optionflags | an int bitmask; `register_optionflag` | `doctest_optionflags` ini | `:options:` plus `doctest_default_flags` | Keep verbatim. `register_optionflag` is the one genuinely cross-library extension point |
| setup / cleanup | `setUp`/`tearDown` on the suite builders | fixtures | `testsetup`/`testcleanup` directives | Author-facing names stay Sphinx's; `phase` is the internal ordering axis; a fixture is never "setup" |
| name | a dotted path; `__lt__` compares it as **text** | node id is `parent.nodeid + "::" + name` | the *group* name, shared by every block in it | `DocTest.name` is a unique machine-independent id. The absolute path lives only in `filename` |

### Data model

```python
class Phase(enum.IntEnum):
    SETUP = 0
    TEST = 1
    CLEANUP = 2


class Block(t.NamedTuple):
    kind: str  # registered BlockKind name
    source: str  # dedented body, verbatim
    want: str | None  # from a paired testoutput
    path: pathlib.Path  # the file the text lives in, not the collected document
    line: int | None  # None when docutils could not recover one
    position: int  # 0-based document pre-order index; the naming key
    groups: tuple[str, ...]  # declared verbatim; () and ("*",) unresolved here
    options: t.Mapping[int, bool]  # plain int keys, exactly as doctest produces
    skipif: str | None  # UNEVALUATED
    hidden: bool


class BlockKind(t.NamedTuple):
    name: str
    phase: Phase
    mode: t.Literal["single", "exec"]
    pairs_with: str | None
    grouped: bool
    node_types: tuple[str, ...]  # docutils tagnames; "comment" for testsetup/:hide:
    option_spec: t.Mapping[str, t.Callable[[str], object]]


class GroupTest(t.NamedTuple):
    group: str
    tests: tuple[doctest.DocTest, ...]  # one per block, in phase order
    globs: dict[str, t.Any]  # the live mapping, shared by every test above
```

`Block.line` being nullable is load-bearing, not defensive. A bare `>>>` block
nested in a `.. note::`, a list item or a block quote reports `line=None,
source=None` from docutils, and an `.. include::`-ed block numbers against the
*included* file. Both propagate to `DocTest.lineno=None` and pytest's honest
"location unknown", rather than to a fabricated number.

`BlockKind.node_types` is likewise load-bearing: `testsetup`, `testcleanup` and
any `:hide:` block are emitted as {class}`docutils.nodes.comment`, not
`literal_block`
([`sphinx/ext/doctest.py:92-93`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L92-L93)).
A walker restricted to `literal_block` silently loses every one of them while the
page still renders.

### Typing

The runtime objects are stdlib's, unconditionally. Precision lives in a parallel
layer that never changes what is constructed.

- **`Protocol` for the seams, nominal subclassing for the concrete classes.**
  `Frontend` is a `Protocol` so a third party can supply one structurally; the
  shipped parser also subclasses {class}`doctest.DocTestParser` so it stays
  passable to `doctest.testfile(parser=...)` and
  {func}`doctest.DocFileSuite`. Typeshed's signatures demand the class, not the
  shape — `DocTestFinder.__init__(parser: DocTestParser = ...)` — so a compatible
  `find()` alone is not enough, which is why `DocutilsDocTestFinder` cannot be
  passed to `DocTestSuite(test_finder=...)` today.
- **`TypedDict` at the docutils boundary.** `BlockAttributes` types what a
  directive stamps on a node, with one narrowing accessor that validates once.
  This is where `Any` currently enters: `str(node.get("test") or ...)` and
  `dict(node.get("options") or {})` are runtime coercions paid for a static hole,
  and typeshed's docutils stub makes it worse — its `get(key, failobj: _T) -> _T`
  claims `_T` even when the key is present holding something else.
- **`t.Literal` for closed vocabularies**, derived from one source of truth so a
  public signature and a config field cannot diverge.
- **Plain `int` keys for optionflags.** {class}`enum.IntFlag` was considered and
  rejected; see [](#alternatives-rejected).
- **`py.typed` ships.** The project already runs mypy strict over `src` and
  `tests`, and the marker file does not exist, so every consumer sees the package
  as untyped. This is a packaging defect independent of the rest of this ADR.

## Constraints

The design is pinned by facts about three upstreams. Each was verified at the tag
cited. The full derivation is in `notes/analyses/`.

### CPython `doctest` (v3.14.2)

| Constraint | Anchor |
|---|---|
| A failure's file line is `test.lineno + example.lineno + 1`; `Example.lineno` is 0-based within the containing string | [`doctest.py:1344`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344) |
| `DocTest.__init__` **copies** the globs mapping, so a shared mapping must be assigned after construction and run with `clear_globs=False` | [`doctest.py:565`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) |
| Never sort collected tests by name: `__lt__` compares names as text, and a name carries its position as text, so `page.md[10]` sorts before `page.md[1]` | [`doctest.py:596`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596) |
| The per-example loop is name-mangled; the supported in-loop seams are the four `report_*` methods and the injected checker | [`doctest.py:1286-1314`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1286-L1314) |
| `run()` mutates global interpreter state for its duration and restores in `finally`; it is neither reentrant nor thread-safe | [`doctest.py:1534-1573`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1534-L1573) |
| Each example compiles under `"<doctest %s[%d]>"` in `"single"` mode with `dont_inherit=True`; `"exec"` suppresses expression echo, emptying every `want` | [`doctest.py:1400`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1400) |
| `TestResults` is a 2-field namedtuple carrying `skipped` as an extra instance attribute; a third tuple field breaks every `failures, tries = runner.run(...)` unpack | [`doctest.py:114`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114) |
| Custom flag names must be registered at import; ints are `1 << len(OPTIONFLAGS_BY_NAME)` and an unregistered name makes a page fail to **parse** | [`doctest.py:153`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L153) |

`report_skip` does not exist at v3.14.2 — the runner has only `report_start`,
`report_success`, `report_failure` and `report_unexpected_exception`. A runner
that owns the loop must probe for it rather than assume it.

### pytest (9.1.1)

| Constraint | Anchor |
|---|---|
| `repr_failure` reads each failure's own `test` — the fact this design is built on | [`doctest.py:317-344`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L317-L344) |
| `DoctestItem.setup()` does `self.dtest.globs.update(globs)`, so the mapping must be mutable and survive collection → setup → run | [`doctest.py:288-293`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L288-L293) |
| `runtest()` calls `run(self.dtest, out=failures)` with `clear_globs` defaulting to `True` — which would empty a shared mapping after the first block | [`doctest.py:295-303`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L295-L303) |
| `PytestDoctestRunner` is defined *inside* `_init_runner_class()` and is not importable, so the `OutcomeException` re-raise, `BdbQuit` → `outcomes.exit` and `continue_on_failure` handling do **not** come for free | [`doctest.py:178-181`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L178-L181) |
| A page must be a `pytest.Module` with `obj = None`, and the collector must call `parsefactories` | [`doctest.py:421`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L421), [`:556`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L556) |
| `_is_doctest` claims any `.txt`/`.rst` **initial path before consulting `--doctest-glob`**, so `pytest docs/page.rst` is claimed by the built-in plugin regardless of glob | [`doctest.py:148-152`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L148-L152) |
| An empty `DocTest` must not be yielded as an item | [`doctest.py:451`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L451) |

### pytest-xdist (v3.8.0)

| Constraint | Anchor |
|---|---|
| Every worker must collect identical node ids in identical order. Violation is not an exception — the scheduler logs `**Different tests collected, aborting run**` and the session executes zero tests | [`load.py:259`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py#L259), [`loadscope.py:359`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L359) |
| The only affinity primitive is `_split_scope(nodeid) -> str`; `loadfile` and `loadgroup` are two-line overrides of it, and `load`/`worksteal` have no scope concept at any layer | [`loadscope.py:284`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284), [`loadfile.py:35`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py#L35) |
| `xdist_group` is honoured only when the *worker's own* `--dist` is `loadgroup`, and works by appending `@name` to `item._nodeid` | [`remote.py:245-254`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254) |
| `parse_tx_spec_config` builds a list, so a negative multiplier contributes zero specs — `xspeclist.extend([spec] * num)`, not a sum | [`workermanage.py:26-37`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26-L37) |

Making the item the sharing unit removes the need to satisfy the first three at
all. The fourth is why `_worker_count` is deleted rather than fixed.

### Sphinx (v9.1.0)

| Constraint | Anchor |
|---|---|
| `testsetup`, `testcleanup` and `:hide:` blocks are emitted as `nodes.comment` | [`doctest.py:92-93`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L92-L93) |
| A `:skipif:`-gated node is dropped during collection, with no outcome, id or count | [`doctest.py:443-444`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L443-L444) |
| `:options:` is accepted only on `doctest` and `testoutput`; a `testcode`'s own options are discarded in favour of its output block's | [`doctest.py:111`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L111), [`:207`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L207) |
| `is_allowed_version(spec, version)` takes the specifier **first** — the reverse of this project's local helper | [`doctest.py:45`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L45) |
| `DocTestBuilder` flips a mutable `self.type` between `"single"` and `"exec"` and reads it through a process-global `doctest.compile` patch | [`doctest.py:310`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L310), [`:548`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/ext/doctest.py#L548) |

## Tensions

Each is a genuine conflict where satisfying one goal costs another. "Both" is not
an answer; the position taken and its price are recorded.

**A vanilla `DocTest` cannot carry the front-end's metadata.** It has exactly
`(examples, globs, name, filename, lineno, docstring)`. *Position:* metadata that
the runner needs rides on a nominal {class}`doctest.Example` subclass —
`doctest.Example` has no `__slots__`, so attributes survive
{func}`copy.copy`, {mod}`pickle`, and a third party's naive
`DocTest(examples, globs, name, filename, lineno, docstring)` rebuild, because
that rebuild reuses the same `Example` objects. Metadata the runner does *not*
need — groups, wildcards, pairing — never touches a stdlib object and dies in the
projection layer. *Price:* one subclass to explain, and a rule that nothing may
smuggle through `DocTest.name`.

**Node-id granularity versus shared state.** *Position:* decouple them — N
`DocTest`s under one node id. *Price:* selecting a group runs all its blocks;
there is no id that names block three alone. That is honest: no surveyed
implementation makes a node id a promise of independent runnability, and the
current `per-block` mode ships ids that raise `NameError` when selected.

**Sphinx's skip versus pytest's skip.** *Position:* pytest's meaning, doctest's
mechanism — set `SKIP`, never drop the node. *Price:* a page carrying a gated
block gains an item relative to `sphinx-build -b doctest`, and `--collect-only`
must not evaluate the gate, which is why `:skipif:` is carried through collection
unevaluated and run in `runtest()`.

**Collection purity versus `--collect-only` fidelity.** *Position:* collection
evaluates no user Python, so it is a pure function of (bytes, argv, ini). *Price:*
`--collect-only` no longer shows which blocks will skip.

**Sphinx compatibility versus silent-loss behaviours.** Sphinx silently discards
an orphan `testoutput`, silently overwrites a duplicate one, and silently drops a
`testcode`'s own `:options:`. *Position:* keep the behaviour, add a diagnostic
with a stable code. *Price:* a page warns under pytest and is silent under
`sphinx-build`; the results still match.

**Owning the loop versus tracking CPython.** *Position:* own it, because
constraint 4 makes it the only way to control compile mode without a
process-global patch or a code-object clone. *Price:* a version shim and a
conformance harness. See {doc}`0002-runner-conformance-across-cpython`.

## What this deletes

`_find`'s monolith · `_merge_blocks` and its padding and clamp ·
`_split_skipped_blocks` and `_lifted_name` · `_exec_mode_run`, `_compile_source`
and `_ExecSource` · `_worker_count` · `_shared_page` and `_is_page` ·
`_splitting_scheduler` and both xdist hooks · the `_init_runner_class` fork ·
`set_blocked("doctest")` and its unblock path.

**The result is not smaller.** It lands roughly flat against the current source.
Under this project's rule that every function carries a NumPy docstring with a
working doctest, splitting one long method into five functions costs prose it did
not previously pay. The value is fewer hazards, not fewer lines: a code-object
clone with a stale globals snapshot, a fork of an upstream parser, node-id string
sniffing, and a method that branches on string literals to decide what a block is
all disappear. Gate on shape instead — a function-length ceiling, a module-length
ceiling, and the `import-linter` contract on the leaf.

(prior-art)=

## Prior art

| Project | Bet | Outcome |
|---|---|---|
| [Sybil 10.0.1](https://github.com/simplistix/sybil/tree/10.0.1) | A document is a flat sequence of non-overlapping character spans; every format is a regex lexer; zero runtime dependencies | Format independence at no dependency cost, and a non-overlap invariant that raises on double collection. But one mutable namespace per document with [one independently selectable item per span](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/integration/pytest.py), so `-k` on a later example raises `NameError`. [Node ids are positional](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/sybil.py#L155-L157) (`line:4,column:1`), so adding a paragraph renames every downstream test. No group support at all — a regex cannot see directive options |
| [xdoctest v1.3.2](https://github.com/Erotemic/xdoctest/tree/v1.3.2) | Abandon stdlib compatibility; own the parser via `ast`/`tokenize`; make directives structured objects | `ast` parsing and structured directives are real advances — [`REQUIRES`](https://github.com/Erotemic/xdoctest/blob/v1.3.2/src/xdoctest/directive.py#L58) carries *why* a block skipped, which a bool cannot. But it is now building compatibility back, and its permissive got/want defaults silently change tests users wrote for stdlib. It unregisters pytest's doctest plugin outright |
| [pytest-examples v0.0.18](https://github.com/pydantic/pytest-examples/tree/v0.0.18) | Emit the canonical form rather than parse it; rewrite expected output in place | Check-mode and update-mode collapse into one path, and byte offsets plus an invertible dedent scalar are what a data model needs to rewrite source. Composes with pytest by contributing no collector at all — the cheapest correct integration in the survey |
| [typeshed](https://github.com/python/typeshed/blob/8c7256c/stdlib/doctest.pyi) | Annotate the 2001 API faithfully | Hands back `Any` at exactly the three extensible points — `globs`, `**options`, `optionflags: int`. Declares `DocTestRunner.test: DocTest` unconditionally although runtime assigns it only inside `run()`, so the stub type-checks a crash |

The collective lesson: **namespace scope is not test identity, markup parsing is
not Python parsing, and runtime compatibility is not static precision.** Every
project conflated at least two, and the first conflation is the one that produces
silent wrong answers rather than inconvenience.

(alternatives-rejected)=

## Alternatives rejected

**Prefix replay** — re-executing a group's predecessors so any block can be
selected standalone. It rebinds `getfixture` to the *replaying* item's request,
so a replayed predecessor resolves different fixture instances: a results
difference, not a performance one. It re-executes gated and deselected blocks
with no node id, in exactly the environment the gate says they must not run in.
It is superlinear precisely where shared groups exist. And it assumes
idempotence, while downstream setup blocks spawn servers and create
repositories.

**One `DocTest` per group whose `docstring` is the whole file.** Attractive —
`lineno=0` and true file lines with no padding — but broken at the two shapes
docutils cannot locate. A nested block reports `line=None`, and an included file
numbers against itself, so one group-wide docstring maps both to confidently
wrong lines, and pytest's per-`DocTest` "location unknown" signal becomes
structurally inexpressible. Per-block `DocTest`s deliver the same benefits with
none of this.

**{class}`enum.IntFlag` as the optionflag surface.** The runtime hash equality is
real and irrelevant to the claims made from it. With a third-party flag
registered — and pytest lazily registers `ALLOW_UNICODE`, `ALLOW_BYTES` and
`NUMBER` in [`_get_flag_lookup`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L385) —
iteration and `repr` silently under-report members outside the enum. And
`Mapping` is invariant in its key type, so `Mapping[Flag, bool]` fails mypy
strict against `dict[int, bool]` in both directions, requiring casts at exactly
the boundaries the change was supposed to clean.

**A registered `EXEC` optionflag to carry compile mode.** It would put compile
mode in the same user-writable namespace as `ELLIPSIS`. A `doctest_optionflags =
EXEC` in any ini, or a stray `# doctest: +EXEC`, compiles in exec mode, which
suppresses expression echo so every `want` compares against empty output and the
suite passes vacuously. Compile mode is an attribute on the `Example` subclass,
unreachable from user configuration.

**Sybil's non-overlap-raises invariant.** Two `.. include::` directives naming
the same file produce blocks over identical source spans. That is a legitimate
page, and an invariant that raises would reject it. Double collection becomes a
diagnostic carrying both provenances.

**Reimplementing `_pytest.doctest`'s helpers instead of importing them.**
Mis-costed by roughly threefold: `_get_checker` alone returns a checker
implementing `ALLOW_UNICODE`, `ALLOW_BYTES` and `NUMBER` with float-precision
handling. Since the plugin still reads `doctest_optionflags` from the built-in
plugin, a project setting `NUMBER` would either raise or — worse — have the bit
accepted and silently do nothing.

**A Sphinx builder.** New scope in a rewrite that must not grow, and both drafts
that proposed one had it deliberately diverging from `sphinx-build -b doctest` on
`:skipif:` and the silent-loss cases. Shipping a builder that disagrees with the
tool it replaces is worse than shipping none.

**An import-time guard that raises.** A `pytest11` plugin raising at import
aborts the whole session, taking down suites whose majority of tests never touch
a doctest. It also checks the wrong property: `hasattr(DocTestRunner,
"_DocTestRunner__run")` is true in exactly the scenario it claims to prevent,
while the thing that actually changed within the supported range —
`__record_outcome`'s arity — is invisible to it. This becomes a differential
conformance test in CI.

## Consequences

### Positive

- Failure locations are correct by construction, including through `.. include::`,
  with no `repr_failure` or `reportinfo` override.
- A block docutils cannot locate degrades to an honest disclaimer instead of a
  fabricated line, and does not affect its siblings.
- Every `--dist` mode works, because there is no shared state to split.
- No CPython code-object clone, and no process-global rebinding of anything.
- Collection is a pure function of (bytes, argv, ini), so worker divergence is
  structurally impossible and `--collect-only` runs no user code.
- Grouping is one pure function with no docutils, pytest or filesystem dependency,
  and is testable without any of them.
- A new block kind is a registration, not an edit to a method branching on string
  literals.
- Parse diagnostics become values with stable codes rather than stderr writes and
  mid-parse aborts.

### Tradeoffs

- The per-example loop is this project's to maintain across supported
  interpreters, including two version-shaped divergences.
- A page containing Sphinx `{testcode}` blocks produces `DocTest`s a stock runner
  cannot run, because `compile("a = 1\nb = 2\n", "<x>", "single")` raises.
  Prompt-form blocks — the overwhelming majority — run perfectly on an unmodified
  runner, and a test asserts it.
- The plugin now *requires* the built-in doctest plugin rather than blocking it,
  so `-p no:doctest` is an error rather than a degraded mode.
- Retiring `namespace_items = per-block` is a real feature removal.
- The line count does not fall.

### Risks

**Runner drift.** A CPython refactor that inlines the loop into `run()` would
silently route execution back to stdlib — invisible for prompt-form blocks,
immediately broken for `{testcode}`. Mitigated by the conformance harness in
{doc}`0002-runner-conformance-across-cpython`, gating on capability probes rather
than a `sys.version_info` ladder.

**pytest private API.** Four private helpers and a subclassed item. Mitigated by
quarantining them in one module behind a pinned matrix; see
{doc}`0006-pytest-private-api-compatibility`.

**Foreign directive registration.** `Sphinx.add_directive` overrides existing
registrations unconditionally, so `sphinx.ext.doctest` loaded in the same
interpreter can replace these directive classes. Mitigated by reading
`BlockAttributes` off the node — byte-compatible with what Sphinx stamps — rather
than depending on this project's own classes having run.

**Over-suppressed diagnostics.** Suppressing one code too many turns a broken page
into a silent zero-test page, which is worse than a mid-parse abort. Mitigated by
the narrow default set in {doc}`0004-diagnostics-as-data`.

## Relationship to other ADRs

This ADR fixes the architecture. Five decisions it defers get their own records:
{doc}`0002-runner-conformance-across-cpython` (how the owned loop is proven
equivalent), {doc}`0003-retiring-per-block-namespace-items` (the deprecation
path), {doc}`0004-diagnostics-as-data` (what is reported and what is suppressed),
{doc}`0005-line-recovery-for-nested-blocks` (the optional last step), and
{doc}`0006-pytest-private-api-compatibility` (the quarantine and its matrix).

## Final position

The core produces real {class}`doctest.DocTest` objects holding real
{class}`doctest.Example` objects, and `Example.source` is the author's verbatim
text. Everything else — groups, phases, pairing, diagnostics, distribution — is a
layer above that fact, and no layer reaches around another.

The unit that shares a `globs` mapping is the unit pytest schedules. That is the
one invariant every other property in this document follows from, and it is not
negotiable for a convenience elsewhere.
