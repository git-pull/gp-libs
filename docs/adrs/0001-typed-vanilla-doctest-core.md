(adr-0001-typed-vanilla-doctest-core)=

# ADR 0001: A typed, vanilla-compatible doctest core

Status: Proposed
Date: 2026-08-02

## Context

### What ships today

`doctest_docutils` re-implements the *finding* half of {func}`doctest.testfile`
over a docutils or MyST doctree and keeps CPython's *running* half.
`pytest_doctest_docutils` wraps that in a pytest plugin.

**Released gp-libs already has per-block identity, and no sharing unit at all.**
`DocutilsDocTestFinder._find` walks the doctree and appends one
{class}`doctest.DocTest` per matched node, named `page.md[k]` where `k` is the
document-order index. The collector yields one {class}`pytest.DoctestItem` per
test. Each test is built by handing `globs` to
{meth}`doctest.DocTestParser.get_doctest`, and `DocTest.__init__` **copies** the
mapping — so every block runs against its own isolated namespace.

That is the real starting point, and it frames the problem precisely: the
granularity this design wants to *preserve* is already shipped. What is missing
is any unit coarser than a block — no groups, no phases, no way for a narrative
page to build state across the prose that explains it.

**The plugin blocks the plugin whose internals it imports.**
`pytest_configure` calls `config.pluginmanager.set_blocked("doctest")`, and the
same module then imports that plugin's private helpers. This survives only
because `_pytest/fixtures.py` has no `pytest_plugin_unregistered` handler, so the
already-parsed `doctest_namespace` fixture outlives unregistration.

### What a shared namespace costs

[PR #87](https://github.com/git-pull/gp-libs/pull/87) is an open, unmerged
attempt at the first problem: it adds Sphinx-style groups, a merge step, phase
ordering, skip lifting, an exec-mode runner and an xdist scheduler. **None of it
has shipped in any release, and none of it is on trunk.** It is described here as
a design under review, not as the status quo, because what it had to build to
work is the evidence this record turns on.

Three costs are worth naming, because a clean-room design must either pay them
again or explain why it does not.

**Merging blocks fights line-number fidelity.** A merged group is one `DocTest`
with one `docstring` and one `lineno`, and both doctest's `%03d` gutter and
pytest's `repr_failure` reconstruct locations by slicing that single string. So
the blocks must be laid out on a synthetic page with blank-line padding and a
clamp, and a wholly-skipped block must be lifted back out to report at all.

**Prompt-free `{testcode}` needs a CPython private.** The per-example loop
[`DocTestRunner.__run`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344)
hard-codes `"single"`
([`Lib/doctest.py:1400`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1400)),
and `sphinx.ext.doctest` gets around that by rebinding `doctest.compile`
process-wide and never restoring it
([`sphinx/ext/doctest.py:310`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L310)) —
unavailable to a library that loads into every pytest session that installed it.
PR #87's answer clones the mangled method's code object into a fresh
{class}`types.FunctionType` whose globals map `compile` to a local helper. That
carries a latent defect: those globals are a snapshot of `vars(doctest)` taken at
import, so a later rebind of a module-level name in `doctest` is invisible to the
clone while remaining visible to the stock runner, and two runners in one process
disagree.

**A live shared mapping forces an xdist fork.** Only execnet-serializable
builtins cross a worker boundary, so a shared namespace must either be merged
into one `DocTest` or kept on one worker. Keeping it there means a scheduler, and
the only affinity primitive in all of xdist is
[`LoadScopeScheduling._split_scope`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284),
a pure function on node-id strings. The controller never collects; it learns the
suite only as node ids arriving from workers. So PR #87 re-derives "these ids
share state" from strings, and re-implements
[`parse_tx_spec_config`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26)
including its quirks.

### The conflation underneath

All three costs follow from one thing. **The granularity of test identity and the
granularity of shared state are different axes, and every surveyed design couples
them.** PR #87's two settings are the clearest illustration: `merged` gives one
`DocTest` and one node id per group; `per-block` gives N `DocTest`s, N node ids
and one live mapping — a node id that raises `NameError` when selected alone.
Sybil ships the second shape without acknowledging it (see [](#prior-art)).

## Decision

**One pytest item owns one shared-state group; inside it, each source block
remains a real, independent {class}`doctest.DocTest`.**

The decoupling is not "group versus block". It is **scheduling identity versus
diagnostic identity**: pytest schedules the group, while each `DocTest` keeps its
own source location, examples and failure gutter.

One {class}`pytest.Item` per (document, group). Inside it, a tuple of per-block
`DocTest`s run in phase order against one live `globs` mapping that never leaves
the item.

The execution shape is not new: `sphinx.ext.doctest` already runs several
`DocTest`s against one shared group namespace. What is new is giving that shape a
**pytest identity**. Sphinx produces no selectable, reportable unit for a group —
every block in it shares one `DocTest.name`, which is why `SphinxDocTestRunner`
overrides a private stdlib method to swallow the resulting `IndexError`. Mapping
the group onto one {class}`pytest.Item` is the contribution.

What that buys, for free and with no override of `repr_failure` or `reportinfo`:
per-block failure locations, per-block gutters, and per-block "location unknown".
Meanwhile `-k`, `--lf`, `-x`, `--reruns` and every `--dist` mode are structurally
incapable of splitting the shared state, because there is only one item to
schedule.

**A per-block `SKIPPED` outcome is not among them.**
{class}`pytest.TestReport`'s `outcome` is one scalar per item, so a group holding
one all-`SKIP` block and one passing block reports `PASSED` with the skip erased.
Signalling the skip instead flips the *whole* group to `SKIPPED`. Surfacing it
per block requires pytest's builtin-but-experimental `subtests` plugin, appears
in the terminal gutter and `-rs` only at `verbosity_subtests >= 1`, and never
becomes a separate `<testcase>`, `--lf` entry or rerunnable unit. See
[](#the-outcome-contract).

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

This is what makes merging unnecessary: the synthetic page, its blank-line
padding and its clamp exist only to reconstruct locations from a single spliced
docstring, and there is no spliced docstring here.

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

**3. Making the item the sharing unit dissolves the *affinity* problem.** A live
mapping never crosses a process boundary, so there is nothing for xdist to split,
under any `--dist` mode. No affinity primitive, no scheduler substitution, no
`parse_tx_spec_config` fork, no node-id string sniffing.

The identical-collection requirement is untouched by this and still binds at any
granularity. It is satisfied separately, by collection being a pure function of
(bytes, argv, ini) — which is why `:skipif:` is carried through collection
unevaluated.

(the-outcome-contract)=

### The outcome contract

One item means one item outcome. That is a real cost of this design and it is
stated here rather than discovered later.

| Signal | Granularity | Notes |
|---|---|---|
| Failure location, `want`/`got`, gutter | **per block** | `repr_failure` iterates failures and reads each one's own `DocTest` |
| `EXAMPLE LOCATION UNKNOWN` | **per block** | a block with `lineno=None` does not affect its siblings |
| `passed` / `failed` / `skipped` | **per item** | `TestReport.outcome` is one scalar |
| JUnit `<testcase>` | **per item** | node reporters are keyed by node id |
| `--lf`, `-k`, `--deselect`, rerun unit | **per item** | |

The skip case is the sharp edge, and it cuts both ways. If the item swallows a
block's skip, a group with one all-`SKIP` block and one passing block reports
`PASSED` and the skip leaves no record — no count, no `-rs` line, no JUnit
`<skipped>`. If the item raises instead, the whole group reports `SKIPPED` even
though a sibling passed. pytest's own doctest plugin takes the second horn only
when *every* example is skipped, via `_check_all_skipped`.

This design takes the same position: **skip the item when every runnable block is
skipped; otherwise report partial skips as typed block detail, not as a pytest
outcome.** No extra reports are synthesized.

"Typed block detail" needs a channel, or implementers will re-invent skip lifting
or write to stderr. The channel is a `GroupResult` — one `BlockResult` per block,
each carrying phase, outcome, gate reason and location — attached to the item and
rendered in two places: the failure longrepr when the group fails, and a
terminal-summary line at `-rs`. It is **not** visible at default verbosity, and
it never becomes a JUnit `<skipped>` entry.

That is a real product loss relative to lifting a gated block into its own item,
and it is accepted deliberately: **a gated block inside a mixed group gives up its
selectable skip row.** The information survives; the addressable unit does not.

`subtests` — a builtin pytest plugin since 9.0, exporting `pytest.Subtests` and
`pytest.SubtestReport` — can emit per-block outcomes, and is the only sanctioned
mechanism that can. It is not adopted here: pytest documents it as experimental,
its output is invisible at default verbosity, and it produces no separate JUnit
entry, so it would buy terminal detail at the cost of depending on an unstable
surface. Revisit if it stabilizes.

### Layers

Dependencies flow one way, from the leaf toward the hosts. No layer may import a
layer above it.

```text
settings            one frozen Settings, resolved once   <- leaf; everything reads it
   |
blocks              inert data: Block, BlockKind, Phase, Diagnostic, Example
   |                (stdlib imports only)
markup/             _rst, _myst, _text, _python -> (blocks, diagnostics)
   |
project             grouping, pairing, phase order, naming -> GroupPlan
   |
runner              owns the per-example loop; phase sequencing
   |
pytest_doctest_docutils   collection, items, globs lifetime, reporting
```

`settings` sits at the bottom, not beside the host, because `Frontend.parse` and
`project()` both take a `Settings`. A layer every other layer reads is a leaf.

| Layer | Owns | Must not know |
|---|---|---|
| `settings` | One frozen `Settings` resolved once, with `None` sentinels at the resolve boundary so a future default change is announceable | pytest's `Config`, argparse, ini format, Sphinx's `app`. The host extracts; this resolves |
| `blocks` | `Block`, `BlockKind` registry, `Phase`, `Diagnostic`, `PlannedBlock`, `GroupPlan`, `ExecutionProfile`, `Example(doctest.Example)` | docutils, MyST, Sphinx, pytest, xdist, the filesystem. Stdlib imports only, enforced by an `import-linter` contract |
| `markup/` | Text → `(blocks, diagnostics)`. **The whole docutils vocabulary**: which node classes each kind may arrive as, the `BlockAttributes` stamp, line-number recovery and its per-front-end meaning, `.. include::` attribution, `nodes.comment` traversal, reporter capture, idempotent directive registration, per-kind `option_spec` | Groups as a runtime concept, `DocTest`, pytest, pairing |
| `project` | The **only** place grouping exists: `*` expansion, anonymous naming, phase order, `testcode`/`testoutput` pairing, option defaults, name minting. A pure function | docutils, pytest, the filesystem, whether anything will run. Evaluates no user code |
| `runner` | `_DocTestRunner__run`; option merge, `SKIP`-after-merge, `FAIL_FAST`, `report_*` dispatch, version shims. `run_group()` owns phase sequencing, run-time `:skipif:`, the profile's context manager, and the `try`/`finally` guaranteeing `testcleanup` | docutils, markup, pytest. Never overrides `run()` |
| `pytest_doctest_docutils` | Options, `Document(pytest.Module)`, `DocutilsItem`, group `globs` lifetime, the outcome contract, built-in-plugin composition, surfacing diagnostics | docutils node classes, MyST configuration, grouping rules |

`pytest_doctest_docutils._compat` is the only module that imports
`_pytest.doctest`, behind a pinned support matrix. See
{doc}`0006-pytest-private-api-compatibility`.

### Item lifecycle

The custom item is load-bearing, and half-reusing {class}`pytest.DoctestItem`
reintroduces the exact bug this design exists to avoid. The contract, stated so
an implementer cannot get it wrong by omission:

1. **Collection** builds one `GroupPlan` per (document, group) and one item per
   plan. An empty plan yields no item.
2. **`setup()`** starts an attempt. In order: clear the live mapping **in place**;
   restore the plan's `seed`, `extraglobs` and `__name__`; then call
   `super().setup()` so fixtures inject into that same object. Clearing in place
   rather than rebinding is what keeps `item.globs is run.globs` true for every
   block, and what stops attempt two of a `--reruns` run from reading attempt
   one's mutations. Every block's `DocTest.globs` is assigned this object *after*
   construction, because `DocTest.__init__` copies.
3. **`runtest()`** is overridden. It must not delegate to
   `DoctestItem.runtest`, which runs a single `dtest` with `clear_globs`
   defaulting to `True` — that would empty the shared mapping after the first
   block. It calls `run_group()`, which runs each `PlannedBlock` in phase order
   with `clear_globs=False`, evaluates `:skipif:` against the live mapping,
   finalizes each paired `want` from its gated `ExpectedOutput`, and wraps the
   body in a `try`/`finally` so cleanup runs whether or not the body raised. When
   cleanup *also* fails, the body's failure is the one raised; cleanup's is
   recorded in the `GroupResult`.

   The `OutcomeException` re-raise, the `bdb.BdbQuit` → `outcomes.exit`
   conversion and `continue_on_failure` are reimplemented here, because
   `PytestDoctestRunner` is nested inside a factory and cannot be imported.
4. **Outcome** follows [](#the-outcome-contract): skip the item only when every
   runnable block is skipped.
5. **`repr_failure`** is inherited unchanged. It already reads each failure's own
   `DocTest`.

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
| test / item / block | `DocTest`, `Example` | `Item` | [`TestCode`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L235) is the parsed unit | Three nouns: `Example` (stdlib), `Block` (parsed), `DocTest` (runnable) |
| skip | the `SKIP` flag, short-circuiting before `report_start` | a reported outcome with a reason, **at item granularity** | [drops the node entirely](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L449-L450) | doctest's mechanism (set `SKIP`, never drop the node); pytest's outcome where the granularity allows it — see [](#the-outcome-contract). Sphinx's drop is deliberately rejected |
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
    profile: ExecutionProfile  # how a body of this kind is compiled and run
    pairs_with: str | None
    grouped: bool


class PlannedBlock(t.NamedTuple):
    phase: Phase
    skipif: str | None  # UNEVALUATED; gated in run_group(), not at collection
    test: doctest.DocTest  # one block, its own filename/lineno/docstring


class GroupPlan(t.NamedTuple):
    group: str
    blocks: tuple[PlannedBlock, ...]  # in phase order; IMMUTABLE
    seed: t.Mapping[str, t.Any]  # initial namespace; copied per attempt


class GroupRun:
    """One execution attempt. Owns the live mapping; a plan never does."""

    plan: GroupPlan
    globs: dict[str, t.Any]  # cleared and reseeded per attempt


class BlockResult(t.NamedTuple):
    block: PlannedBlock
    outcome: t.Literal["passed", "failed", "skipped"]
    reason: str | None  # the gate expression, when skipped


class GroupResult(t.NamedTuple):
    group: str
    blocks: tuple[BlockResult, ...]
    failures: tuple[doctest.DocTestFailure | doctest.UnexpectedException, ...]
```

`Block.line` being nullable is load-bearing, not defensive. A bare `>>>` block
nested in a `.. note::`, a list item or a block quote reports `line=None,
source=None` from docutils, and an `.. include::`-ed block numbers against the
*included* file. Both propagate to `DocTest.lineno=None` and pytest's honest
"location unknown", rather than to a fabricated number.

`PlannedBlock` exists because `run_group()` owns phase sequencing, run-time
`:skipif:` evaluation and a cleanup `finally` — and cannot do any of the three
from a bare tuple of `DocTest`s. A `DocTest` carries no phase and no gate, so the
plan has to. Tagging each entry also makes the ordering self-describing rather
than a convention a comment asserts.

**A `PlannedBlock.test` cannot always be fully preconstructed.** Sphinx accepts
`:skipif:` on a `testoutput`, and when that output is gated away its `testcode`
still runs — expecting *empty* output. So the `want` of a paired block is a
function of a gate evaluated at run time, and the plan must carry the paired
output as data (`ExpectedOutput`, itself gated) with the `DocTest` finalized in
`run_group()`. Freezing `want` at projection time silently runs the wrong
assertion.

**A wildcard block needs a distinct `DocTest` per group it joins.** `DocTest.globs`
is a plain mutable attribute, so one object shared across two `GroupPlan`s would
have the second group's assignment win and both groups would execute against one
mapping. `*` membership therefore materializes a separate `DocTest` per group.

**The gate's evaluation namespace is a deliberate divergence.** Sphinx evaluates
each `:skipif:` in a fresh context seeded with `doctest_global_setup`; this design
evaluates it against the live group mapping, after fixture injection and after
earlier blocks have run. That is more useful — a gate can consult a fixture — and
it is not what `sphinx-build` does. Recorded rather than hidden.

`ExecutionProfile` is a **private** protocol carrying compile mode, extra compile
flags, and an optional per-group context manager. It is not a `Literal["single",
"exec"]`, because a second execution policy already exists in this repository:
[PR #59](https://github.com/git-pull/gp-libs/pull/59) adds top-level `await`,
which needs `ast.PyCF_ALLOW_TOP_LEVEL_AWAIT` and an event-loop lifetime that a
mode string cannot express. The profile's context manager is what `run_group()`
enters, so that lifetime is served without overriding `run()` and stdlib's
save-and-restore `finally` stays inherited. It stays private until a caller
outside the package needs it; PR #59 is the in-repo caller that justifies it
existing at all.

**Which docutils node classes a kind may arrive as is a front-end concern, not a
`BlockKind` field.** `testsetup`, `testcleanup` and any `:hide:` block are
emitted as {class}`docutils.nodes.comment`, not `literal_block`
([`sphinx/ext/doctest.py:92-93`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L92-L93)),
and a walker restricted to `literal_block` silently loses every one of them while
the page still renders. That requirement is real, but it belongs to `markup/`
alongside the rest of the node vocabulary — putting it on `BlockKind` would drag
docutils into a layer declared stdlib-only.

### Typing

The runtime objects are stdlib's, unconditionally. Precision lives in a parallel
layer that never changes what is constructed.

- **`Protocol` for the seams, nominal subclassing for type-checkability.**
  `Frontend` is a `Protocol` so a third party can supply one structurally. The
  shipped parser *also* subclasses {class}`doctest.DocTestParser` — not because
  the interpreter requires it (stdlib `doctest` performs no `isinstance` check on
  `parser` or `test_finder`; a duck-typed object works at runtime) but because
  typeshed's signatures name the class, so a checker rejects what the interpreter
  accepts. The subclass buys type-checkability, not passability. Passability is a
  matter of matching the call signature: a finder whose `find()` takes a string
  first cannot be handed to `DocTestSuite`, which passes a module — and
  subclassing does not fix that.

  One genuine nominal edge does exist: `DocTestSuite` sorts its results, and
  `DocTest.__lt__` returns `NotImplemented` for a non-`DocTest`, so a custom
  finder must return real `DocTest` objects.
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
| A page must be a `pytest.Module` with `obj = None` as a **class** attribute, or the `Module` machinery tries to import the `.rst`/`.md` file | [`doctest.py:420-421`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L420-L421) |
| Conftest autouse fixtures reach page items through `FixtureManager.pytest_plugin_registered`, **not** through a collector calling `parsefactories` — that call is `DoctestModule`-only, for fixtures defined in the collected `.py` itself | [`fixtures.py`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/fixtures.py), [`doctest.py:556`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L556) |
| `_is_doctest` claims any `.txt`/`.rst` **initial path before consulting `--doctest-glob`**, so `pytest docs/page.rst` is claimed by the built-in plugin regardless of glob | [`doctest.py:148-152`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L148-L152) |
| An empty `DocTest` must not be yielded as an item | [`doctest.py:451`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L451) |

### pytest-xdist (v3.8.0)

| Constraint | Anchor |
|---|---|
| Every worker must collect identical node ids in identical order. Violation is not an exception — the scheduler logs `**Different tests collected, aborting run**` and the session executes zero tests | [`load.py:259`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py#L259), [`loadscope.py:359`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L359) |
| The only affinity primitive is `_split_scope(nodeid) -> str`; `loadfile` and `loadgroup` are two-line overrides of it, and `load`/`worksteal` have no scope concept at any layer | [`loadscope.py:284`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284), [`loadfile.py:35`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py#L35) |
| `xdist_group` is honoured only when the *worker's own* `--dist` is `loadgroup`, and works by appending `@name` to `item._nodeid` | [`remote.py:245-254`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254) |
| `parse_tx_spec_config` builds a list, so a negative multiplier contributes zero specs — `xspeclist.extend([spec] * num)`, not a sum | [`workermanage.py:26-37`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26-L37) |

Making the item the sharing unit removes the need to satisfy the second and third
at all. **The first still binds at any granularity** — identical collection is
required whether a page yields one item or fifty — and is approached instead
through determinism over source closure, normalized settings and a frozen
registry, not through a purity claim collection cannot make. The fourth is why a
worker-count fork is not worth carrying: `pytest_xdist_setupnodes(config, specs)`
hands over the already-expanded spec list and never raises.

There is a fifth hazard the single-item shape also removes, worth naming because
it has no guard otherwise: a worker crash re-runs only the *uncompleted* items of
a work unit on a fresh process, so blocks 3..N of a shared group would run
against an empty mapping. Worker restarts are on by default.

### Sphinx (v8.2.3, the version this project resolves)

| Constraint | Anchor |
|---|---|
| `testsetup`, `testcleanup` and `:hide:` blocks are emitted as `nodes.comment` | [`doctest.py:92-93`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L92-L93) |
| A `:skipif:`-gated node is dropped during collection, with no outcome, id or count | [`doctest.py:449-450`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L449-L450) |
| `:options:` is **not in `TestcodeDirective.option_spec`**, so writing it on a `testcode` is an unknown-option error that drops the block — a loud rejection, not a silent discard | [`doctest.py:174-180`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L174-L180), [`:111`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L111) |
| `:pyversion:` **is** in `TestcodeDirective.option_spec` and is silently ignored there — the real silent loss on a testcode | [`doctest.py:177`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L177) |
| Cleanup does **not** run when setup fails: the group returns early | [`doctest.py:554-556`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L554-L556) |
| `is_allowed_version(spec, version)` takes the specifier **first** | [`doctest.py:45`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L45) |
| `DocTestBuilder` flips a mutable `self.type` between `"single"` and `"exec"` and reads it through a process-global `doctest.compile` patch | [`doctest.py:310`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L310), [`:549`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L549) |

Sphinx v9.1.0 changes the default group an unargumented block joins. Any
group-naming behaviour matched against "Sphinx" has to say which Sphinx, and
{doc}`0005-line-recovery-for-nested-blocks` proposes moving this floor.

## Tensions

Each is a genuine conflict where satisfying one goal costs another. "Both" is not
an answer; the position taken and its price are recorded.

**A vanilla `DocTest` cannot carry the front-end's metadata.** It has exactly
`(examples, globs, name, filename, lineno, docstring)`. *Position:* metadata the
runner needs at run time rides on a {class}`doctest.Example` subclass —
`doctest.Example` has no `__slots__`, so attributes survive {func}`copy.copy`,
{mod}`pickle`, and a third party's naive
`DocTest(examples, globs, name, filename, lineno, docstring)` rebuild, because
that rebuild reuses the same `Example` objects. Metadata the runner does *not*
need — groups, wildcards, pairing — never touches a stdlib object and dies in the
projection layer.

*Price:* the subclass must restore equality, because
{meth}`doctest.Example.__eq__` gates on **exact type identity**
([`Lib/doctest.py:518`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L518)) —
a bare subclass compares unequal to a stock `Example` with identical fields, in
both directions, while hashing the same. So the subclass overrides `__eq__` with
an {func}`isinstance` check and re-binds `__hash__` explicitly; Python's
reflected-operand rule then makes equality symmetric again:

```{doctest}
>>> import doctest
>>> class Tagged(doctest.Example):
...     def __eq__(self, other):
...         if not isinstance(other, doctest.Example):
...             return NotImplemented
...         return (self.source, self.want, self.lineno, self.indent,
...                 self.options, self.exc_msg) == (
...                other.source, other.want, other.lineno, other.indent,
...                other.options, other.exc_msg)
...     __hash__ = doctest.Example.__hash__
>>> plain, tagged = doctest.Example("1\n", "1\n"), Tagged("1\n", "1\n")
>>> tagged == plain, plain == tagged, tagged in [plain]
(True, True, True)

Without the override, a bare subclass is unequal both ways:

>>> class Bare(doctest.Example): pass
>>> bare = Bare("1\n", "1\n")
>>> bare == plain, plain == bare
(False, False)
```

The alternative — setting the attribute on a *stock* `Example` with no subclass
at all — is equality-safe by construction and equally durable. It is rejected
only because it forfeits the typed surface; if the subclass ever proves
troublesome, that is the fallback.

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

**Collection determinism versus `--collect-only` fidelity.** *Position:*
collection evaluates no *author-supplied* Python — `:skipif:` is carried through
unevaluated and run in `runtest()`. *Price:* `--collect-only` no longer shows
which blocks will skip.

Collection is **not** a pure function of (bytes, argv, ini), and claiming so
would be wrong on four counts: `.. include::` reads transitive files, docutils
directive implementations execute during parsing, the directive registry is
process-global, and MyST plugins change the tree. The defensible contract is
determinism over **complete source closure + normalized settings + frozen
registry**. Deferring the author's gate removes the largest divergence risk; it
does not make xdist divergence structurally impossible, and the
{doc}`registry freeze <0006-pytest-private-api-compatibility>` is what closes the
rest.

**Sphinx compatibility versus silent-loss behaviours.** Sphinx silently discards
an orphan `testoutput`, silently discards a `testoutput` following a `doctest`
block, silently overwrites a duplicate `testoutput`, and silently ignores
`:pyversion:` on a `testcode`. *Position:* keep the behaviour, add a diagnostic
with a stable code for each of the four. *Price:* a page warns under pytest and
is silent under `sphinx-build`; the results still match.

**Guaranteed cleanup versus Sphinx's setup-failure short-circuit.** When setup
fails, Sphinx returns before the cleanup phase, skipping page `testcleanup`
blocks and `doctest_global_cleanup` alike. *Position:* run cleanup
unconditionally in a `try`/`finally`, because a page that spawns a server in
setup and fails mid-way should not leak it. *Price:* a page whose setup fails
leaves different residue under pytest than under `sphinx-build`, and that is a
deliberate divergence rather than an oversight.

**Owning the loop versus tracking CPython.** *Position:* own it, because
constraint 4 makes it the only way to control compile mode without a
process-global patch or a code-object clone. *Price:* a version shim and a
conformance harness. See {doc}`0002-runner-conformance-across-cpython`.

## What this avoids

Only one item here exists on trunk today: `set_blocked("doctest")` and its
unblock path, which {doc}`0006-pytest-private-api-compatibility` replaces. The
rest are machinery [PR #87](https://github.com/git-pull/gp-libs/pull/87) has to
build to make a shared namespace work, and which this shape never needs:

- the merge step, its blank-line padding and its `max()` clamp
- skip lifting, which pulls a wholly-skipped block back out of a running group
- the code-object clone with its stale `vars(doctest)` snapshot
- the worker-count fork of `parse_tx_spec_config`
- the node-id string sniffing that infers "these ids share state"
- the scheduler substitution and both xdist hooks

**The result is not smaller.** It lands roughly flat against a finder that does
the same job.
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
- Collection runs no author-supplied Python, so `--collect-only` has no side
  effects and the largest source of worker divergence is removed.
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
equivalent), {doc}`0003-rejecting-per-block-items` (the deprecation
path), {doc}`0004-diagnostics-as-data` (what is reported and what is suppressed),
{doc}`0005-line-recovery-for-nested-blocks` (the optional last step), and
{doc}`0006-pytest-private-api-compatibility` (the quarantine and its matrix).

## Final position

The core produces real {class}`doctest.DocTest` objects holding real
{class}`doctest.Example` objects. `Example.source` is the stdlib-normalized
executable body — prompts and indentation stripped, trailing newline added, the
stripped column recorded in `Example.indent` — not a synthesized wrapper and not
the author's verbatim text, which is what `Block.source` holds. Everything else —
groups, phases, pairing, diagnostics, distribution — is a layer above that fact,
and no layer reaches around another.

The unit that shares a `globs` mapping is the unit pytest schedules. That is the
one invariant every other property in this document follows from, and it is not
negotiable for a convenience elsewhere.
