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

The execution shape is partly precedented. `sphinx.ext.doctest` runs several
`DocTest`s against one shared group namespace — but only for the *test* phase.
All of a group's `testsetup` blocks are combined into a **single** simulated
`DocTest` named `f"{group.name} (setup code)"`, and likewise cleanup; only
`group.tests` is one `DocTest` per block
([`sphinx/ext/doctest.py:525-556`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L525-L556)).

So this design is per-block in all three phases where Sphinx is per-block in one,
and — more importantly — Sphinx produces no selectable, reportable unit for any
of them: every ordinary test block in a group shares one `DocTest.name`, which is
why `SphinxDocTestRunner` overrides a private stdlib method to swallow the
resulting `IndexError`. Mapping the group onto one {class}`pytest.Item` while
each block keeps its own identity is the contribution.

With the default checker that buys, for free and with no override of
`repr_failure` or `reportinfo`: per-block failure locations, per-block gutters,
and per-block "location unknown".
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
siblings**. The default-checker path requires no override of `repr_failure` or
`reportinfo`.

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
granularity. It is approached separately through deterministic projection over
the complete source closure, normalized settings and a frozen registry — which
is why `:skipif:` is carried through collection unevaluated.

(the-outcome-contract)=

### The outcome contract

One item means one item outcome. That is a real cost of this design and it is
stated here rather than discovered later.

| Signal | Granularity | Notes |
|---|---|---|
| Failure location, `want`/`got`, gutter | **per block** | default `repr_failure` iterates failures and reads each one's own `DocTest`; custom checkers use the same locations in the narrow rendering branch |
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

This design takes the same position over the test phase: **skip the item when
every `Phase.TEST` block is skipped; otherwise report partial skips as typed block
detail, not as a pytest outcome.** Setup and cleanup are infrastructure and do
not contribute a passed or skipped test. No extra reports are synthesized.

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

Dependencies flow from the hosts toward small foundations. No foundational
layer imports a host, and configuration never owns discovered capabilities.

```text
contracts       settings        model
    \              |              /
     +--------- registry --------+
                    |
                 markup
                    |
                 project
                    |
                  runner
                    |
          direct / pytest / Sphinx hosts
```

| Layer | Owns | Must not know |
|---|---|---|
| `contracts` | Public protocols and immutable contribution records: `DocumentParser`, `ExecutionProfile`, `ExecutionRuntime`, `CheckerFactory`, `Contributor` and `Registrar` | Sphinx, pytest, xdist and host lifecycle objects. Only stdlib and public parser types cross this boundary |
| `settings` | Three immutable facets — `ParseSettings`, `ProjectionSettings`, `RunSettings`. `None` sentinels at the resolve boundary make a future default change announceable | registries, pytest's `Config`, argparse, ini format, Sphinx's `app`. The host extracts; this resolves |
| `model` | `ParsedBlock`, `ParsedOutput`, `BlockKind`, `Phase`, `Diagnostic`, `ProjectedBlock`, `GroupPlan`, `RunContext` and the result types. **No stdlib subclasses.** | docutils, MyST, Sphinx, pytest, xdist, the filesystem. Stdlib imports only |
| `registry` | A private mutable builder and the public immutable `RegistrySnapshot` consumed by every later layer | host lifecycle objects after the snapshot is frozen |
| `markup/` | Text → `(blocks, diagnostics)`. **The whole docutils vocabulary**: which node classes each kind may arrive as, the `BlockAttributes` stamp, line-number recovery and its per-front-end meaning, `.. include::` attribution, `nodes.comment` traversal, reporter capture, idempotent directive registration, per-kind `option_spec` | Groups as a runtime concept, `DocTest`, pytest, pairing |
| `project` | The **only** place grouping exists: `*` expansion, anonymous naming, phase order, `testcode`/`testoutput` pairing, option defaults, name minting. A pure function | docutils, pytest, the filesystem, whether anything will run. Evaluates no user code |
| `runner` | `_DocTestRunner__run`; option merge, `SKIP`-after-merge, `FAIL_FAST`, `report_*` dispatch, version shims. `run_group()` owns phase sequencing, run-time `:skipif:`, the profile's context manager, and the `try`/`finally` guaranteeing `testcleanup` | docutils, markup, pytest. Never overrides `run()` |
| `pytest_doctest_docutils` | Options, `Document(pytest.Module)`, `DocutilsItem`, group `globs` lifetime, the outcome contract, built-in-plugin composition, surfacing diagnostics | docutils node classes, MyST configuration, grouping rules |

`pytest_doctest_docutils._compat` is the only module that imports
`_pytest.doctest`, behind a pinned support matrix. See
{doc}`0006-pytest-private-api-compatibility`.

### Settings and the frozen registry

Settings have **lifetimes**, not just precedence. "Resolve exactly once at session
start" cannot be true of document front matter, which does not exist until that
document is parsed. Three scopes:

| Scope | Owns | Resolved |
|---|---|---|
| `SessionSettings` | defaults plus normalized host configuration | once, before collection or direct execution |
| `DocumentSettings` | the front-matter overlay a page is permitted to set | per document, after parsing |
| block / example policy | directive options, then inline `# doctest:` flags | per block, at projection and run |

Not every field shares one ladder, so the precedence is stated per axis. For
option flags it follows Sphinx: **runner defaults → directive or output
`:options:` → inline flags.**

Two fields move out of the core entirely. **Encoding** belongs to the source
loader, because `DocumentParser` already receives `str`. **Report style** belongs
to the host adapter. And wildcard resolution and name minting are *invariants*,
not user-configurable knobs — exposing them would let a project produce node ids
no other project can read.

`ProjectionSettings.ungrouped` defaults to `"default"`. An unlabelled runnable
block therefore joins the page's `default` group unless the user explicitly asks
for block isolation. This clean-slate default follows Sphinx's author vocabulary
and makes state-sharing opt-out rather than a project-specific surprise.

The **registry** is a separate input resolved after `SessionSettings`. "Frozen"
means the public `RegistrySnapshot` contains immutable mappings and records; the
mutable builder is private and discarded. Registering after the host freezes its
snapshot is an error. Keeping these values separate matters under xdist: settings
are normalized user input, while the snapshot is the capability set discovered in
that process.

**Contribution and the snapshot are public; mutation is not.** The stated goal is
an extendable, pluggable core, so a small host-neutral contributor protocol ships
in v1. Front ends, block kinds, execution profiles and checkers all feed one
builder and every consumer receives the same `RegistrySnapshot`. Host-specific
registration timing is a separate decision; the core contract does not import a
pytest hook or a Sphinx application.

The direct, pytest and Sphinx lifecycles, including the xdist consistency check,
are specified in {doc}`0007-host-plugin-registration-lifecycle` so this record
does not mistake a host bootstrap policy for a core dependency.

### Item lifecycle

The custom item is load-bearing, and half-reusing {class}`pytest.DoctestItem`
reintroduces the exact bug this design exists to avoid. The contract, stated so
an implementer cannot get it wrong by omission:

0. **The carrier.** {class}`pytest.DoctestItem` reads `self.dtest` in
   `setup()`, `reportinfo()` and `_check_all_skipped()`, so the subclass must
   define it even though a group holds many tests. `self.dtest` is a synthetic
   **zero-example** `DocTest` for the group, and its `globs` **is** the canonical
   live mapping — the same object every `RunnableBlock`'s test is given. That
   makes the inherited `setup()` inject fixtures into exactly the right place
   with no override of the injection itself.

1. **Collection** builds one `GroupPlan` per (document, group) and one item per
   plan. An empty plan yields no item.
2. **`setup()`** starts an attempt. In order: clear the live mapping **in place**;
   restore the plan's `seed`, `extraglobs` and `__name__`; then call
   `super().setup()` so fixtures inject into that same object. Clearing in place
   rather than rebinding is what keeps `item.globs is run.globs` true for every
   block, and what stops attempt two of a `--reruns` run from reading attempt
   one's mutations. Each `RunnableBlock` is materialized against this object —
   its `DocTest.globs` assigned *after* construction, because `DocTest.__init__`
   copies.
3. **`runtest()`** is overridden. It must not delegate to
   `DoctestItem.runtest`, which runs a single `dtest` with `clear_globs`
   defaulting to `True` — that would empty the shared mapping after the first
   block. It calls `run_group()`, which materializes and runs each
   `RunnableBlock` in phase order with `clear_globs=False`, evaluates `:skipif:`
   and `:pyversion:` against the live mapping and interpreter,
   finalizes each paired `want` from its gated `ExpectedOutput`, and wraps the
   body in a `try`/`finally` so cleanup runs whether or not the body raised. When
   cleanup *also* fails, the body's failure is the one raised; cleanup's is
   recorded in the `GroupResult`.

   The `OutcomeException` re-raise, the `bdb.BdbQuit` → `outcomes.exit`
   conversion and `continue_on_failure` are reimplemented here, because
   `PytestDoctestRunner` is nested inside a factory and cannot be imported.
4. **Outcome** follows [](#the-outcome-contract): only `Phase.TEST` blocks
   determine pass versus skip. A plan with no test block yields no item. Setup and
   cleanup are infrastructure: an error there may fail or abort the item, but a
   successful setup is not a passed test and a cleanup skip cannot erase the test
   result. Skip the item only when every test block is skipped.
   `runtest()` must also keep `_disable_output_capturing_for_darwin()`, which
   the inherited implementation calls before running and which has nothing to do
   with grouping.

5. **Failure projection** flattens every `Failed.failures` tuple in block order
   and raises pytest's `MultipleDoctestFailures`. With the default pytest checker,
   `repr_failure` is inherited unchanged and therefore preserves pytest's exact
   output. A contributed checker must supply both `check_output` and
   `output_difference`; the item takes one small custom-rendering branch so the
   checker that decided the failure also explains it. `repr_failure` does not
   render `GroupResult`. Partial-skip detail goes to a report section and the
   terminal summary; see [](#the-outcome-contract).

6. **Reporting across processes.** The controller never sees the item — it
   receives serialized `TestReport` dictionaries. So `pytest_runtest_makereport`
   copies a **versioned, JSON-safe** block summary onto the report. The summary
   contains only the schema version, group name, block name, phase, outcome,
   counts and structured skip reason — never exceptions or live objects. pytest
   serializes arbitrary report attributes and xdist reconstructs them
   controller-side. The rich `GroupResult`, and every exception in it, stays
   worker-local.

### Vocabulary

Goal (e) — speaking doctest's, pytest's *and* Sphinx's idioms — is mostly a
naming problem, because the three overload the same nouns with different
referents. Each term below is decided once and used only that way.

| Term | doctest | pytest | Sphinx | Decision |
|---|---|---|---|---|
| `globs` | the dict examples exec in; [`DocTest.__init__` stores a **copy**](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) | — | assigned to `test.globs` after construction, run with `clear_globs=False` | Keep `globs` for the mapping |
| namespace | — | [`doctest_namespace`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L721) means *injected names* | — | **Not** used for the sharing unit; pytest owns the word |
| group | — | `xdist_group` is a *scheduling* affinity marker ([`remote.py:245-254`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254)) | the author-facing bucket: `.. doctest:: intro`, `default`, `*` | Adopt `group` for the sharing unit. The xdist affinity key is *derived*, never the group name |
| scope | — | the fixture-lifetime ladder | — | Reserved for pytest. The real question is what an *unlabelled* block joins, so the setting is `ungrouped = "default" | "block"`, not a `share` axis |
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


# --- contracts: public, host-neutral extension seams ----------------------


Failure: t.TypeAlias = doctest.DocTestFailure | doctest.UnexpectedException


class RuntimeOutcome(t.NamedTuple):
    results: doctest.TestResults
    failures: tuple[Failure, ...]


class RuntimeSettings(t.NamedTuple):
    optionflags: int
    continue_on_failure: bool
    checker: doctest.OutputChecker


class CheckerFactory(t.Protocol):
    def __call__(self) -> doctest.OutputChecker: ...


class ExecutionRuntime(t.Protocol):
    def run(self, test: doctest.DocTest) -> RuntimeOutcome: ...


class ExecutionProfile(t.Protocol):
    def open(
        self, settings: RuntimeSettings
    ) -> contextlib.AbstractContextManager[ExecutionRuntime]: ...


# --- parsed: inert, produced by extraction, owns no semantics -------------


class ParsedBlock(t.NamedTuple):
    kind: str  # registered BlockKind name
    source: str  # dedented body, verbatim author text
    path: pathlib.Path  # the file the text lives in, not the collected document
    line: int | None  # None when docutils could not recover one
    document_order: int  # position among blocks AND outputs; the pairing key
    block_ordinal: int  # position among runnable blocks; the identity key
    groups: tuple[str, ...]  # declared verbatim; () and ("*",) unresolved here
    options: t.Mapping[int, bool]  # plain int keys, exactly as doctest produces
    skipif: str | None  # UNEVALUATED
    pyversion: str | None  # UNEVALUATED PEP 440 specifier
    hidden: bool


class ParsedOutput(t.NamedTuple):
    """A `testoutput` body. Not a block: it never runs."""

    text: str
    path: pathlib.Path
    line: int | None
    document_order: int  # shares one sequence with ParsedBlock for pairing
    groups: tuple[str, ...]
    options: t.Mapping[int, bool]
    skipif: str | None  # a gated output means its testcode expects nothing
    pyversion: str | None


class BlockKind(t.NamedTuple):
    phase: Phase
    profile_name: str  # resolved against the frozen registry, not held here
    pairs_with: str | None
    grouped: bool


# --- projected: one per block, with everything the runner needs ------------


class ExpectedOutput(t.NamedTuple):
    text: str
    options: t.Mapping[int, bool]
    skipif: str | None  # when truthy at run time, `want` becomes ""
    pyversion: str | None  # when disallowed at run time, `want` becomes ""


class ExampleRecipe(t.NamedTuple):
    """Everything needed to rebuild one stock `doctest.Example`."""

    source: str
    want: str
    exc_msg: str | None
    lineno: int  # 0-based, relative to the block's docstring
    indent: int
    options: t.Mapping[int, bool]


class ProjectedBlock(t.NamedTuple):
    """A RECIPE. Holds no `DocTest`, because a `DocTest` is mutable."""

    phase: Phase
    name: str  # the minted test name
    block_ordinal: int  # stable among runnable blocks before filtering
    examples: tuple[ExampleRecipe, ...]  # a prompt block yields SEVERAL
    docstring: str  # what pytest's failure renderer slices
    filename: str
    lineno: int | None  # the block's own line; examples are relative to it
    options: t.Mapping[int, bool]  # block-level directive :options:
    profile_name: str  # resolved against the frozen registry per attempt
    skipif: str | None  # UNEVALUATED; gated in run_group()
    pyversion: str | None  # UNEVALUATED; gated in run_group()
    expected: ExpectedOutput | None  # paired testoutput, itself gateable


class GroupPlan(t.NamedTuple):
    group: str
    blocks: tuple[ProjectedBlock, ...]  # in phase order; STRUCTURALLY immutable
    seed: t.Mapping[str, t.Any]  # initial namespace; copied per attempt


# --- run: one attempt materializes fresh stdlib objects --------------------


class RunnableBlock(t.NamedTuple):
    """Materialized per attempt. Its `DocTest` is never retained by a plan."""

    recipe: ProjectedBlock
    test: doctest.DocTest  # fresh stock objects, built this attempt
    runtime: ExecutionRuntime  # from the profile factory, this attempt


class RunContext:
    """One execution attempt. Owns the live mapping; a plan never does."""

    plan: GroupPlan
    globs: dict[str, t.Any]  # cleared in place and reseeded per attempt
    runtimes: dict[str, ExecutionRuntime]  # one per profile used by the group


# --- results: a discriminated union, so invalid states cannot be built -----


class Counts(t.NamedTuple):
    attempted: int
    skipped: int  # a PASSING block can still carry skipped examples


class SkipReason(t.NamedTuple):
    kind: t.Literal["skipif", "inline-flag", "pyversion", "profile"]
    detail: str  # the gate expression, the flag, the specifier


class Passed(t.NamedTuple):
    block: ProjectedBlock
    counts: Counts


class Failed(t.NamedTuple):
    block: ProjectedBlock
    counts: Counts
    # PLURAL: continue_on_failure yields several from one block
    failures: tuple[Failure, ...]


class Skipped(t.NamedTuple):
    block: ProjectedBlock
    counts: Counts
    reason: SkipReason


class Errored(t.NamedTuple):
    block: ProjectedBlock
    error: BaseException  # a gate that raised, or a runtime that would not start


BlockResult: t.TypeAlias = Passed | Failed | Skipped | Errored


class GroupResult(t.NamedTuple):
    group: str
    blocks: tuple[BlockResult, ...]
    primary: BaseException | None  # what runtest() re-raises
    secondary: tuple[BaseException, ...]  # e.g. cleanup failing after the body
```

`ParsedBlock` carries no `want`, because neither owner of a `want` is the parsed
block: for a prompt-form block it is *inside* `source` and
{class}`doctest.DocTestParser` extracts it at projection, and for a
`testcode`/`testoutput` pair it is a separate `ParsedOutput`. Conflating the two
was what made "projection owns pairing" untrue.

`document_order` is one monotonic sequence shared by runnable blocks and
`ParsedOutput` records. Pairing therefore follows the source stream even when an
output sits between two runnable candidates. `block_ordinal` counts runnable
blocks only and survives gating, filtering and wildcard expansion, so adding or
removing expected output cannot rename every later test. Both `:skipif:` and
`:pyversion:` remain data until the run boundary; collection never evaluates
either gate.

`BlockKind` names a profile rather than holding one, so a public type never
contains a private implementation. The profile name and the block kind's own
registration name resolve against the frozen registry.

**A plan holds no `DocTest`.** {class}`doctest.DocTest` is mutable — the design
assigns `globs` to it after construction, and a run mutates that mapping — so a
plan retaining one would not be a recipe, it would be last attempt's state. Under
`--reruns` that is the false-green this design exists to prevent. `ProjectedBlock`
therefore carries the *ingredients*, and `RunContext` materializes fresh stock
`Example` and `DocTest` objects for every attempt.

**The ingredients are per example, not per block.** One prompt block routinely
yields several {class}`doctest.Example` objects, each with its own `source`,
`want`, `exc_msg`, `lineno`, `indent` and `options` — three, for a block whose
last statement raises:

```{doctest}
>>> import doctest
>>> src = ">>> x = 1\n>>> x + 1\n2\n>>> int('z')\nTraceback (most recent call last):\nValueError: bad\n"
>>> test = doctest.DocTestParser().get_doctest(src, {}, "blk", "p.md", 0)
>>> len(test.examples)
3
>>> [(e.lineno, e.want.strip()) for e in test.examples]
[(0, ''), (1, '2'), (3, 'Traceback (most recent call last):...')]
```

A single `source` and one `lineno` cannot represent that, and `docstring` is
separately required by pytest's known-location failure renderer. Hence
`ExampleRecipe` and `ProjectedBlock.docstring`: the recipe reproduces exactly what
{meth}`doctest.DocTestParser.get_doctest` produced, rather than approximating it.

The same applies to a gated `testoutput`: when its gate is truthy the output is
**absent**, not empty. Its text *and* its output-specific options both disappear,
which is what Sphinx does, and which a pre-built `want=""` with retained options
would get wrong.

`GroupPlan` is **structurally** immutable, not deeply so. Its tuples cannot be
rebound, but `seed` is a `Mapping` whose *values* are arbitrary user objects. Each
attempt shallow-copies it into the live mapping, which is exactly what
`DocTest.__init__` does with `globs` — matching doctest's own namespace semantics
rather than inventing a deeper guarantee the ecosystem does not provide.

**Results are a discriminated union**, not one record with nullable fields, so
"passed with an exception attached" is unrepresentable rather than merely
unlikely. `Errored` exists because a gate that raises, or a runtime that will not
start, is none of pass, fail or skip.

Four result details are load-bearing:

- **`Failed.failures` is plural.** Under `continue_on_failure` one block reports
  several failures; a singular field silently keeps the first.
- **`Passed` carries counts.** A block can pass *and* have skipped examples —
  `failed=0 attempted=2 skipped=1` — and a result type without counts loses the
  skip entirely, which is the same information ADR 0001's outcome contract
  promises to surface.
- **`Skipped` carries counts too.** A whole-block gate attempts zero examples,
  while an all-`SKIP` doctest has parsed examples and reports them skipped. The
  reason alone cannot distinguish those cases.
- **`SkipReason` is typed.** A skip originates from `:skipif:`, an inline
  `# doctest: +SKIP`, `:pyversion:`, or a profile declining to run — and "the gate
  expression" describes only the first.

**Exception precedence is phase-aware, not a single ladder.** Grouping
{exc}`KeyboardInterrupt`, a debugger quit, {exc}`pytest.skip`, `xfail` and
`pytest.exit` into one "control-flow" tier is unsafe. A cleanup skip must not erase
a real test failure, while a session exit must never be converted into block data.

| Class | Examples | Rule |
|---|---|---|
| process, debugger or session abort | {exc}`KeyboardInterrupt`, `SystemExit`, `bdb.BdbQuit`, `pytest.exit` | always propagates from every phase; cleanup still runs, but cannot replace it |
| host outcome from setup or test | `pytest.skip`, `pytest.xfail` | propagates as the host outcome after cleanup |
| doctest mismatch from test | `DocTestFailure`, `UnexpectedException` | retained in source order and projected to the host after cleanup |
| runtime error from setup or test | a gate that raises, or a profile that cannot start | recorded as `Errored`; becomes the primary failure when no abort or host outcome exists |
| cleanup exception or cleanup host outcome | any exception, including `pytest.skip` or `pytest.xfail` | recorded as `secondary` when a primary exists; otherwise becomes the item failure, never a skip or xfail |

Profile runtimes are entered through {class}`contextlib.ExitStack`, so a partial
startup unwinds deterministically in reverse. Classifying which exceptions are
pytest outcomes is the pytest adapter's job; the core knows only the phase.

`ParsedBlock.line` being nullable is load-bearing, not defensive. A bare `>>>` block
nested in a `.. note::`, a list item or a block quote reports `line=None,
source=None` from docutils, and an `.. include::`-ed block numbers against the
*included* file. Both propagate to `DocTest.lineno=None` and pytest's honest
"location unknown", rather than to a fabricated number.

`ProjectedBlock` carries phase and gate because `run_group()` owns phase
sequencing, run-time `:skipif:` evaluation and a cleanup `finally` — and cannot do
any of the three from a bare tuple of `DocTest`s. A `DocTest` carries no phase and
no gate, so the recipe has to. Tagging each entry also makes the ordering
self-describing rather than a convention a comment asserts.

**A paired `want` is not known until run time.** Sphinx accepts
`:skipif:` on a `testoutput`, and when that output is gated away its `testcode`
still runs — expecting *empty* output. So the `want` of a paired block is a
function of a gate evaluated at run time, and the plan must carry the paired
output as data (`ExpectedOutput`, itself gated) with the `DocTest` finalized in
`run_group()`. Freezing `want` at projection time silently runs the wrong
assertion.

**A wildcard block is projected separately per group it joins.** Projection
clones the recipe and mints a group-qualified name for each destination. Each
`RunContext` then builds its own `DocTest` from its own recipe. Reusing one
`ProjectedBlock` would make its name ambiguous; sharing one materialized
`DocTest` would be worse, because `DocTest.globs` is mutable and the second
group's assignment would win.

**The gate's evaluation namespace is a deliberate divergence.** Sphinx evaluates
each `:skipif:` in a fresh context seeded with `doctest_global_setup`; this design
evaluates it against the live group mapping, after fixture injection and after
earlier blocks have run. That is more useful — a gate can consult a fixture — and
it is not what `sphinx-build` does. Recorded rather than hidden.

**`ExecutionProfile` is an immutable factory; `ExecutionRuntime` is per attempt.**
A group can mix prompt, `exec` and async blocks, so there is no single per-group
profile. The profile is chosen per block and names a factory; `RunContext` creates
one runtime *per distinct profile* the group uses, and blocks sharing a profile
share its runtime. An async runtime therefore owns one event loop for the whole
group, which is what lets awaited state cross block boundaries.

It is not a `Literal["single", "exec"]`, because a second execution policy already
exists in this repository: [PR #59](https://github.com/git-pull/gp-libs/pull/59)
adds top-level `await`, which needs `ast.PyCF_ALLOW_TOP_LEVEL_AWAIT` and an
event-loop lifetime a mode string cannot express. The runtime's context manager is
what `run_group()` enters, so that lifetime is served without overriding `run()`
and stdlib's save-and-restore `finally` stays inherited.

**The ordinary lane does not use the owned loop at all.** For prompt-form blocks —
the overwhelming majority — the runner is a plain reporter subclass over CPython's
*untouched* per-example loop. `_DocTestRunner__run` is invoked only for extended
profiles: `exec` bodies, top-level await, and whatever comes next. Ordinary
doctests are then compatible **by construction** rather than by differential
testing, and {doc}`0002-runner-conformance-across-cpython`'s harness shrinks to
guarding the extended lane.

**A checker owns both comparison and explanation.** The default pytest
registration constructs pytest's checker, preserving `ALLOW_UNICODE`,
`ALLOW_BYTES`, `NUMBER` and its inherited failure representation exactly. A
contributed `CheckerFactory` constructs a fresh checker for each runtime. The
same instance performs `check_output()` and `output_difference()`; using pytest's
private `_get_checker()` only at rendering time would let one checker reject the
example and another explain why.

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

- **Parsing and extraction are two seams, not one.** A single
  `DocumentParser.parse(text, path)` cannot serve Sphinx, because a Sphinx extension
  already *has* a doctree and a raw re-parse is not the same tree. So:

  ```python
  class DocumentParser(t.Protocol):
      """Text -> doctree. Plural implementations: _rst, _myst, third-party."""

      suffixes: t.ClassVar[frozenset[str]]

      def parse(
          self, text: str, path: pathlib.Path, *, settings: ParseSettings
      ) -> tuple[nodes.document, tuple[Diagnostic, ...]]: ...


  def extract_blocks(
      doctree: nodes.document, *, settings: ParseSettings
  ) -> ParseResult: ...
  ```

  `extract_blocks` is deliberately a plain function, not a `Protocol`: exactly
  one extractor is the *point* of the split, and a second implementation would
  reintroduce the standalone-versus-Sphinx divergence it exists to prevent.
  Standalone reST and MyST use both halves; a Sphinx extension calls only the
  extractor, on the doctree it already resolved.

  **`DocumentParser` is not a {class}`doctest.DocTestParser`.** The two
  signatures are incompatible — stdlib's is `parse(self, string, name='<string>')`
  returning alternating `str` and `Example`, and `get_doctest` depends on exactly
  that
  ([`Lib/doctest.py:657`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L657),
  [`:696`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L696)).
  So there are three lanes, not one:

  | Lane | Contract |
  |---|---|
  | plain text and strings | the exact `DocTestParser` contract, unmodified |
  | reST / MyST | `DocumentParser` → doctree → `extract_blocks` |
  | Python objects | a `DocTestFinder`-shaped adapter |

  Anything promising `DocFileSuite(parser=...)` compatibility is a separate
  stdlib-shaped façade over the first lane, not the markup lane wearing a
  stdlib name.

  This is not a Sphinx builder. A builder owns discovery, an `env`, an `outdir`
  and a reporting format; an extractor is a pure function from a doctree to
  blocks, and {doc}`0001-typed-vanilla-doctest-core`'s rejection of a builder
  stands.

- **Python object discovery is not a front end.** Finding doctests in a module's
  docstrings takes an *object*, not `(text, path)`, and stdlib already has the
  right shape for it. It is a {class}`doctest.DocTestFinder`-shaped adapter, and
  putting a `_python` module in `markup/` was a category error.

- **`Protocol` for markup seams; nominal classes only for stdlib façades.**
  `DocumentParser` is a `Protocol` so a third party can supply one structurally.
  It must not subclass {class}`doctest.DocTestParser`: their `parse()` signatures
  and return types are incompatible, so the apparent typeshed accommodation is
  itself an invalid override. The optional `DocFileSuite` façade instead owns a
  separate nominal `DocTestParser` adapter with the exact stdlib signature.
  Runtime passability still comes from matching the called method: a finder whose
  `find()` takes a string first cannot be handed to `DocTestSuite`, which passes a
  module, and subclassing does not fix that.

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

### What "vanilla-compatible" promises

The phrase is worth decomposing, because it covers several different promises of
several different strengths.

| Surface | Promise |
|---|---|
| `Example` / `DocTest` runtime types | **Exact.** Stock instances, never subclassed for metadata |
| plain-text parsing | **Exact.** The stdlib lane uses `DocTestParser` unmodified |
| option flags and checkers | **Exact.** `register_optionflag` and the stdlib checker contract, with pytest's `ALLOW_UNICODE`/`ALLOW_BYTES`/`NUMBER` reachable |
| prompt-block execution | **Exact.** CPython's own per-example loop, unmodified |
| `DocTestFinder`-shaped Python-object discovery | **Shaped**, as a separate adapter |
| `DocFileSuite` / `DocTestSuite` | **Façade only**, over the stdlib lane. A group plan cannot be expressed through an API that returns one `DocTest` per parser call |
| `{testcode}`, async, groups, phases, Sphinx gates | **Deliberate extension.** No stdlib equivalent to be compatible with |
| pytest collection, fixtures, reporting | pytest's own contracts, composed with rather than replaced |
| Sphinx **node** vocabulary | **Exact.** The `BlockAttributes` stamp is byte-compatible |
| Sphinx **execution** | **Not promised.** See below |

**The Sphinx promise is narrow, and this record narrows it deliberately.** What is
offered is an *extractor over a Sphinx-resolved doctree* — a pure function from a
doctree to blocks, callable from an extension.
{doc}`0007-host-plugin-registration-lifecycle` defines how Sphinx extensions
contribute capabilities, but not a Sphinx execution lifecycle or result channel.
Inventing those would be the builder that [](#alternatives-rejected) turns down.
The record promises doctree consumption and nothing more.

## Constraints

The design is pinned by facts about three upstreams. Each was verified at the tag
cited. The full derivation is in `notes/analyses/`.

### CPython `doctest` (v3.14.2)

| Constraint | Anchor |
|---|---|
| A failure's file line is `test.lineno + example.lineno + 1`; `Example.lineno` is 0-based within the containing string | [`doctest.py:1344`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344) |
| `DocTest.__init__` **copies** the globs mapping, so a shared mapping must be assigned after construction and run with `clear_globs=False` | [`doctest.py:565`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) |
| Never sort collected tests. `__lt__` compares `(name, filename, lineno, id(self))`; `name` leads, so a name carrying its position as text sorts `page.md[10]` before `page.md[1]` however correct `lineno` is. `filename` and `lineno` only break ties among equal names | [`doctest.py:596-603`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596-L603) |
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
`(examples, globs, name, filename, lineno, docstring)`. *Position:* all extension
metadata stays on `ProjectedBlock`, `RunContext` and the result records. Stock
`DocTest` and `Example` objects remain exact compatibility objects, not metadata
carriers. *Price:* a consumer holding only the stdlib object sees only stdlib
semantics; it must retain the core recipe to inspect groups, profiles or gates.

Putting metadata on an `Example` subclass is rejected because
{meth}`doctest.Example.__eq__` gates on exact type identity
([`Lib/doctest.py:518`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L518)),
so a bare subclass is unequal to a stock `Example` with identical fields in both
directions while hashing the same. Restoring equality with an {func}`isinstance`
override then over-corrects: two *unrelated* subclasses compare equal to each
other, and to any third party's bare subclass.

```{doctest}
>>> import doctest
>>> def tagged(name):
...     ns = {"__eq__": lambda s, o: isinstance(o, doctest.Example)
...           and s.source == o.source, "__hash__": doctest.Example.__hash__}
...     return type(name, (doctest.Example,), ns)
>>> Exec, Await = tagged("Exec"), tagged("Await")
>>> Exec("1\n", "1\n") == Await("1\n", "1\n")
True
```

A block's execution policy is **uniform across its examples**, so it belongs on
`ProjectedBlock`, not on the examples. The runner establishes an *active
execution request* immediately before delegating to stdlib `run()` and clears it
in a `finally`; `_DocTestRunner__run` reads it. Stock `Example` objects stay
stock, and nothing in the compatibility kernel is subclassed for metadata at all.

**Node-id granularity versus shared state.** *Position:* decouple them — N
`DocTest`s under one node id. *Price:* selecting a group runs all its blocks;
there is no id that names block three alone. That is honest: no surveyed
implementation makes a node id a promise of independent runnability, and the
proposed shared per-block shape would expose ids that raise `NameError` when
selected without their predecessors.

**Sphinx's skip versus pytest's skip.** *Position:* pytest's meaning, doctest's
mechanism — set `SKIP`, never drop the node. *Price:* a page carrying a gated
block gains an item relative to `sphinx-build -b doctest`, and `--collect-only`
must not evaluate the gate, which is why `:skipif:` is carried through collection
unevaluated and run in `runtest()`.

**Collection determinism versus `--collect-only` fidelity.** *Position:*
collection evaluates no *author-supplied* Python — `:skipif:` is carried through
unevaluated and run in `runtest()`. *Price:* `--collect-only` no longer shows
which blocks will skip.

(the-collection-contract)=

Collection is **not** a pure function of (bytes, argv, ini), and claiming so
would be wrong on five counts: `.. include::` reads transitive files, docutils
directive implementations execute during parsing, the directive registry is
process-global, MyST plugins change the tree, and the frozen registry is itself
an input — assembled from installed plugins and conftests, neither of which is
argv or ini. The defensible contract is
determinism over **complete source closure + normalized settings + frozen
registry** — all three defined above. Deferring the author's gate removes the
largest divergence risk; it does not make xdist divergence structurally
impossible.

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
suite passes vacuously. Execution policy is selected by
`ProjectedBlock.profile_name`, outside the user-writable optionflag namespace.

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

- Failure locations are correct by construction, including through `.. include::`;
  the default-checker path needs no `repr_failure` or `reportinfo` override.
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

This ADR fixes the architecture. Six decisions it defers get their own records:
{doc}`0002-runner-conformance-across-cpython` (how the owned loop is proven
equivalent), {doc}`0003-rejecting-per-block-items` (why shared per-block items
are rejected), {doc}`0004-diagnostics-as-data` (what is reported and what is
suppressed), {doc}`0005-line-recovery-for-nested-blocks` (the optional last
step), {doc}`0006-pytest-private-api-compatibility` (the quarantine and its
matrix), and
{doc}`0007-host-plugin-registration-lifecycle` (host registration and freeze
points).

## Final position

The core produces real {class}`doctest.DocTest` objects holding real
{class}`doctest.Example` objects. `Example.source` is the stdlib-normalized
executable body — prompts and indentation stripped, trailing newline added, the
stripped column recorded in `Example.indent` — not a synthesized wrapper and not
the author's verbatim text, which is what `ParsedBlock.source` holds. Everything
else — groups, phases, pairing, diagnostics, distribution — is a layer above that
fact, and no layer reaches around another.

The unit that shares a `globs` mapping is the unit pytest schedules. That is the
one invariant every other property in this document follows from, and it is not
negotiable for a convenience elsewhere.
