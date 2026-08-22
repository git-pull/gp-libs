# Writing

How this project writes prose, for humans and agents alike. It governs
`README.md`, `CHANGES`, release notes, commit messages, docstrings, source
comments, log messages, and the Markdown and reStructuredText under `docs/`
— every surface a reader reaches.

For environment setup, the gates, and pull request workflow, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Voice

Three surfaces, one voice. A docstring says what a caller may rely on; a
`CHANGES` entry says what changed; prose says what happens. All three are
present tense, lead with the thing being described, and stop. Why it was
built that way belongs in the commit message, which is timestamped and
attached to the diff.

The most useful editing operation is deleting the introductory sentence.

Lead with verbs and name concrete things. Put identifiers in backticks.
Prefer short declarative sentences, one operational fact each. Do not
explain Python to Python developers; do explain this project's semantics.

Type annotations describe shape. Documentation describes meaning. A sentence
that restates a signature has said nothing.

Use MUST, SHOULD, and MAY only where the normative sense is meant. Say what
actually happens rather than that something is "supported".

| Instead of                       | Prefer                            |
| --------------------------------- | --------------------------------- |
| "We added…"                      | "`DocutilsDocTestFinder.find` now accepts…" |
| "New and improved"               | "`linkify_issues` now…"           |
| "powerful", "seamless"           | state the capability              |
| "easily", "simply", "just"       | omit                              |
| "simple", "obvious", "intuitive" | omit                              |
| "robust"                         | name the failure that is handled  |
| "comprehensive"                  | name what is covered              |
| "production-ready"               | state the guarantee               |
| "optimized", "blazingly fast"    | give the magnitude                |
| "various fixes"                  | name the components               |
| "under the hood"                 | omit unless observable            |
| "please note that", "note that"  | state the fact                    |
| "leverage", "utilize"            | "use"                             |
| "delve into"                     | "read", or omit                   |
| "best practices"                 | name the practice                 |
| "in order to"                    | "to"                              |

## Who you are writing for

The default reader is wiring gp-libs into their own project: pointing pytest
at `docs/` with `pytest_doctest_docutils`, running
`python -m doctest_docutils README.md` by hand, or adding `linkify_issues`
to a Sphinx `conf.py`. They are fluent in pytest and Sphinx as users —
`conftest.py`, fixtures, `extensions`, `testpaths` — and write
reStructuredText or Markdown daily, but you cannot assume they know
gp-libs' internals: docutils node traversal, directive registration, or how
the finder decides a block is a doctest.

A second, smaller reader works *on* gp-libs or against its lower layers:
the doctest finder, the docutils compatibility shims, myst-parser directive
registration, or contributing. Serve them too, but mark their material
opt-in ("for the rarer cases", "advanced") so the default reader knows they
can stop. Never make the common case pay a comprehension tax for the
advanced one.

Rules that follow:

- **Second person, present tense, active.** "You point pytest at `docs/`",
  not "Files are collected". Address the reader who is doing the thing.
- **Concept before configuration.** Open by saying what the tool *is* and
  what it does for the reader. The `conf.py` key, the pytest flag — those
  are the last details they need, not the first. A page that opens with
  "set these keys" has buried the idea under its mechanics.
- **Say when they can stop.** Lead with the default and the reassurance:
  install the plugin and `pytest docs/` just works; `issue_url_tpl` is the
  one setting `linkify_issues` needs. Let a skimmer leave after one
  paragraph.
- **Grant permission, do not demand attention.** "Reach for this when…"
  tells readers they are in the right place without implying they must read
  on.
- **Progressive disclosure.** Order by how many readers need it: the
  default → the one option a few will tune (a custom `issue_re`,
  `--doctest-docutils-modules`) → running `doctest_docutils` directly → the
  docutils machinery underneath. Each step is for a smaller audience than
  the last.
- **Lean on the pipeline.** The reader thinks in a chain: a `.rst` or `.md`
  file is parsed (docutils, with myst-parser for Markdown), its examples
  are collected, then run. Reinforce that chain when explaining why
  Markdown needs myst-parser or why a fixture needs a visible
  `conftest.py`.
- **Name the trade-off.** If a choice costs something — the plugin disables
  pytest's standard doctest plugin, Markdown support goes through
  myst-parser, fixtures reach only files a `conftest.py` can see — say so,
  and say what it buys. State it; do not sell it.
- **Frame by concept, not by mechanism.** Do not headline a feature by its
  `conf.py` key or pytest flag in prose; that names the implementation
  surface, the reader's last concern. Name the concept. The mechanics
  vocabulary — the flag spelling, the default regex — belongs in a
  reference block or the API section, and only there.

`docs/modules/linkify_issues/index.md` is the worked example: a
concept-first intro that says what the extension does (plain-text `#123`
becomes a link) before any `conf.py` key, a two-step default configuration
most readers can stop after, `issue_re` marked as optional tuning for the
smaller audience, an honest close that more complex needs mean forking,
and the API reference last.

## README

A README is the shortest path from "what is this?" to competent use, not
the project's autobiography.

The first sentence is a contract. It says what abstraction the reader has
been handed, concretely enough to tell this package apart from the
neighbouring one.

Get to a runnable command or snippet before anything the reader can skip.
A logo, a mission statement, a comparison matrix and three paragraphs of
history in front of the install line all cost the same thing.

State the minimum Python version and meaningful platform constraints in
prose, not only in badges. `requires-python` in `pyproject.toml` is the
authority; the README must agree with it.

Examples are executable, not illustrative fiction. See
[Documented examples that run](#documented-examples-that-run) for which
blocks are executed and how to write one that qualifies.

Document the semantic model, not the flag list. `--help` already
enumerates flags, and gp-libs has none — it ships two pytest plugin
components, a Sphinx extension, and a CLI entry point on
`doctest_docutils` itself. What prose can say that a flag list cannot is
precedence, which files each collector reaches, and what a passing or
failing run means.

State defaults explicitly — defaults are API. State negative guarantees
where they exist: "no `doctest_namespace` fixtures are registered for
`docs/`", "the pytest plugin blocks pytest's own doctest collection". They
establish boundaries faster than any amount of description.

Headings stay conventional and stable, because people deep-link them.
Badges are few and load-bearing.

## Documented examples that run

Examples in this fleet are tests, and gp-libs is what makes that true: it
ships the collector every other repo in this fleet relies on. This section
documents every format `doctest_docutils` and `pytest_doctest_docutils`
actually support, verified against `src/doctest_docutils.py` and
`src/pytest_doctest_docutils.py` — not the aspirational set.

**A fence tag is cosmetic; only a `>>> ` prompt executes.** A block written
as

    ```python
    finder = DocutilsDocTestFinder()
    ```

is prose that looks like a test. Nothing collects it, nothing runs it, and
it can be wrong for years. The same block written with prompts is a test:

    ```python
    >>> finder = DocutilsDocTestFinder()
    ```

This is the single most expensive mistake available when editing
documentation, because removing the prompts leaves a green test suite and
a silently deleted test. When editing a file that contains examples, count
the prompts before and after.

**The fence tag is `python`.** Not `pycon`, not bare. This is uniform
across the fleet and tooling depends on it — even though, for gp-libs
specifically, the underlying finder is looser than the convention: it
matches any fenced block whose content matches doctest's own prompt regex,
regardless of the language tag on the fence. Do not rely on that; a `text`
or `pycon` fence with a working `>>> ` example is an accident other tools
in the fleet will not replicate. Use `python`.

**Two independent collection paths.** `.py` files are handed straight to
pytest's own `DoctestModule` — the same class pytest's built-in `doctest`
plugin uses, called directly rather than through that plugin's hooks. This
repo's plugin registers under the `pytest11` entry-point key `sphinx` (see
`[project.entry-points.pytest11]` in `pyproject.toml`), and on
`pytest_configure` it blocks pytest's own `doctest` plugin
(`config.pluginmanager.set_blocked("doctest")`) so a `.py` docstring is
never collected twice. `.rst` and `.md` files go through
`DocutilsDocTestFinder` instead: it parses the file with docutils (`.rst`)
or myst-parser (`.md`), then walks the resulting tree for anything
doctest-shaped. A file's presence in `testpaths` (`pyproject.toml`) makes
it eligible for either path; only prompts make a block executable.

**Where examples run in this repo.** `testpaths` lists `tests`, `docs`,
and `src`, so `.py` docstrings under `src/`, `.md` files under `docs/`,
and `.py` files under `tests/` are all collected. `README.md` is *not*
listed in `testpaths`, so pytest never reaches any of its three `>>> `
prompts today — do not describe the README as tested. Keep the prompts as
prompts anyway: dropping a `>>> ` silently deletes what would otherwise be
a test, and the count (`rg -c '^\s*>>> ' README.md`) is the guard against
that. Note that adding `README.md` to `testpaths` would not make all three
runnable as-is — two of them are `>>> ` lines nested inside a fence that
is itself illustrating `.. doctest::`/`{doctest}` syntax as text, one
fence-level too deep for the finder's regex fallback to see past. Only the
bare `doctest_block` example would collect. Making the other two
executable, not just illustrative, would need its own follow-up.

**Formats the finder collects**, for `.rst` and `.md`:

- **A bare `>>> ` prompt.** Docutils' own `doctest_block` node type — a
  plain paragraph starting with `>>> ` needs no directive in
  reStructuredText. In Markdown this needs a fence (` ```python `); myst
  gives you the same node.
- **The `.. doctest::` directive** (reStructuredText) or the
  ` ```{doctest} ``` ` fence (MyST Markdown). Both register through the
  same `DoctestDirective` class. Options, all read from `self.options` on
  the directive:
  - `:options:` — inline doctest flags, e.g. `+ELLIPSIS -NORMALIZE_WHITESPACE`.
  - `:pyversion:` — a PEP 440 specifier (checked with `is_allowed_version`);
    the example is skipped when the running interpreter does not satisfy
    it.
  - `:skipif:` — an expression the runner evaluates to decide whether to
    skip.
  - `:trim-doctest-flags:` / `:no-trim-doctest-flags:` — whether
    `# doctest: +FLAG` comments are stripped from the rendered code before
    display.
  - `<BLANKLINE>` in the block content is doctest's own convention for an
    intentional blank line in expected output; it works here exactly as in
    stdlib doctest, and the directive additionally pretty-prints it back to
    a real blank line in the built HTML.
- **`.. testsetup::` / `.. testcleanup::`** (or the ` ```{testsetup} ``` `
  / ` ```{testcleanup} ``` ` fences). These render as hidden comments
  instead of a visible code block, which is the entire effect they have:
  each one is still an independent doctest that needs its own `>>> `
  prompts to execute, and — unlike Sphinx's `sphinx.ext.doctest` — it does
  **not** share globals with the doctest blocks around it. Each collected
  block gets its own copy of the file's globals
  (`doctest.DocTest.__init__` copies `globs`), so a variable a
  `testsetup` block assigns is gone by the next block. Nothing in this
  repo's own documentation currently uses `testsetup`/`testcleanup`; the
  only exercise they get is in `tests/`. Treat them as "hide this from the
  rendered page" rather than "shared fixture for the examples that
  follow" — write the setup you need directly into each example instead.

**Flags.** `ELLIPSIS` and `NORMALIZE_WHITESPACE` are enabled globally via
`doctest_optionflags` in `pyproject.toml`, so `...` elides variable output
and whitespace differences do not fail a comparison. The stdlib flag set
(`ELLIPSIS`, `NORMALIZE_WHITESPACE`, `IGNORE_EXCEPTION_DETAIL`,
`DONT_ACCEPT_BLANKLINE`, `SKIP`, and the rest of
`doctest.OPTIONFLAGS_BY_NAME`) all work as usual. `pytest_doctest_docutils`
additionally registers, via `doctest.register_optionflag`:

- `ALLOW_UNICODE` / `ALLOW_BYTES` — ignore a `u''`/`b''` string prefix
  mismatch. These are not gp-libs inventions: they are the same flags
  pytest's own (now-blocked) `doctest` plugin defines, re-registered here
  so `.rst`/`.md` collection — which builds its own runner and reuses
  pytest's checker (`_pytest.doctest._get_checker()`) — gets identical
  behaviour to a `.py` doctest.
- `NUMBER` — also borrowed from pytest's checker: ignores floating-point
  precision beyond what the literal in the expected output states.
- `HIDE` — the one flag that is actually gp-libs' own. It is a **no-op for
  execution**: the output checker never consults it, so `+HIDE` never
  changes whether an example passes. Registering it exists for one reason
  — so `# doctest: +HIDE` *parses* instead of raising
  `ValueError: invalid option`. It is a signal for documentation tooling
  that wants to know "this example should run as a test but not appear in
  rendered output"; gp-libs itself does not act on that signal anywhere.
  `HIDE` is registered eagerly in `pytest_configure`, before any
  docstring is parsed, because the `.py` collection path never calls the
  function (`_get_flag_lookup`) that registers `ALLOW_UNICODE`,
  `ALLOW_BYTES`, and `NUMBER` — without the eager registration, a `.py`
  docstring using `+HIDE` would fail to parse.

**`# doctest: +SKIP` is not permitted** in this fleet's own documentation.
It is a workaround that tests nothing. `doctest_docutils` supports it
mechanically — `tests/test_doctest_options.py` proves the mechanism works,
because gp-libs is the tool and has to prove its own flags function — but
that is a test of the tool, not licence to write `+SKIP` into a page. Use
the fixtures, `pyversion`, or `skipif` instead.

**Do not downgrade a doctest to a non-executed block to make it pass.** A
`.. code-block::` or an unprompted fence does not run. If an example
cannot pass, fix the example or fix the code.

**No `doctest_namespace` fixtures anywhere in this repo.** A `conftest.py`
only reaches files inside its own subtree, and the only `conftest.py` in
this repo lives at `tests/conftest.py` — invisible to `src/` and `docs/`.
Add objects to `doctest_namespace` from a fixture when you need shared
helpers for a group of `.rst`/`.md` examples:

```python
import pytest


@pytest.fixture
def add_helpers(doctest_namespace):
    def add(left, right):
        return left + right

    doctest_namespace["add"] = add
```

— but until such a fixture exists and is visible to the file you are
editing, keep documentation examples self-contained: import what you use
inside the block.

**Docstring examples** use the NumPy `Examples` section:

    Examples
    --------
    >>> is_allowed_version('3.3', '<=3.5')
    True

**gp-libs dogfoods two more mechanisms most repos in this fleet do not.**
`docs/conf.py` adds `sphinx.ext.doctest` to `extra_extensions` and sets
`doctest_global_setup` (importing `is_allowed_version` and
`pytest_ignore_collect`), so the `{doctest}` blocks under `docs/` are also
valid input to Sphinx's own doctest builder, not only to pytest. Running
that builder is `just -f docs/justfile doctest` — a real recipe, but one
`tests.yml` and `docs.yml` never invoke. Treat it as a manual,
local-only check: useful when you are debugging a `docs/conf.py` change,
not a gate anything is blocked on. `uv run pytest` is what actually proves
a documentation example runs in CI.

## The changelog

`CHANGES` is the changelog. Not `CHANGELOG.md`. It is rendered as
[the project's changelog page](https://gp-libs.git-pull.com/history.html)
via `docs/history.md`.

A ledger, not a narrative. It is scanned, and the question a reader is
asking is whether an entry affects them. Modeled on Django's release-notes
shape — deliverables get titles and prose, not bullets.

**Release entry boilerplate.** Every release header is
`## gp-libs X.Y.Z (YYYY-MM-DD)`. The file opens with a
`## gp-libs X.Y.Z (unreleased)` placeholder block fenced by
`<!-- KEEP THIS PLACEHOLDER ... -->` and
`<!-- END PLACEHOLDER ... -->` HTML comments — new release entries land
immediately below the END marker, never above it.

**Open with a multi-sentence lead paragraph.** Plain prose, no italic.
Open with the version as sentence subject ("gp-libs X.Y.Z ships …") so the
lead is self-contained when excerpted. Two to four sentences telling the
reader what shipped and who cares — user-visible takeaways, not internal
mechanism. Cross-reference detail docs with `{ref}` to keep the lead
compact.

**Unreleased entries carry no lead paragraph and no version summary.**
Speaking for a release — what the version "is", "ships", or "focuses on"
— is presumptuous before its scope is final. Only the person cutting the
release writes that, and only when the user explicitly asks to release.
Never write or edit a lead paragraph from a feature branch, and never ask
or imply that a release should happen.

**Each deliverable is a section, not a bullet.** Inside `### What's new`,
every distinct deliverable gets a `#### Deliverable title (#NN)` heading
naming it in user vocabulary, followed by one to three prose paragraphs
explaining what shipped. Do not wrap a paragraph in `- ` — bullets are for
enumerable lists, not paragraph containers. Cross-link detail docs
(`See {ref}\`foo\` for details.`) so prose stays focused.

**The deliverable test.** Before writing an entry, ask: "What's the
deliverable, in user vocabulary?" If you cannot answer in one sentence,
the entry isn't ready. Mechanism — helper internals, byte counters,
schema-validation locations — belongs in pull request descriptions and
code comments, not the changelog.

**Fixed subheadings**, in this order when present: `### Breaking changes`,
`### Dependencies`, `### What's new`, `### Fixes`, `### Documentation`,
`### Development`. Dev tooling (helper scripts, internal automation) lives
under `### Development`. For breaking changes, show the migration path
with concrete inline code (a `# Before` / `# After` fenced block).
Dependency floor bumps use the form
``Minimum `pkg>=X.Y.Z` (was `>=X.Y.W`)``.

**PR refs `(#NN)`** sit in each deliverable's `####` heading.

**When bullets are appropriate.** Catch-all sections (`### Fixes`,
occasionally `### Documentation`) with three or more genuinely small items
use bullets — one line each, never paragraphs. If a bullet swells past two
lines, promote it to a `#### Title (#NN)` heading with a prose body.

**Anti-patterns.** Fragile metrics that go stale silently — token
ceilings, third-party version pins, percent benchmarks, exact byte counts.
Describe the capability, not the math. Private symbols (leading-underscore
identifiers) and algorithm names exposed for the first time. Walls of text
dressed up as bullets. Breaking changes buried mid-entry instead of given
their own subheading at the top.

**Always link autodoc'd APIs.** Any class, method, function, exception, or
attribute that has its own rendered page must be cited with its role
(`{class}`, `{meth}`, `{func}`, `{exc}`, `{attr}`) — never plain backticks.
Doc pages without an explicit ref label use `{doc}`. Plain backticks are
correct for code syntax, environment variables, parameter names, and file
paths that are not doc pages — anything without an autodoc destination.

**Summarization style.** When asked "what changed in the latest version?",
lead with the entry's lead paragraph (paraphrased if needed), followed by
each `####` deliverable heading under `### What's new` with a one-sentence
summary. Cite `(#NN)` only if asked for source links. Do not invent
versions, dates, or numbers not present in `CHANGES`. Do not quote line
numbers or file offsets — those shift as the file evolves.

## Release notes

`CHANGES` is the permanent ledger; a release page is editorial. Lead with
one paragraph naming the headline change, then three to five highlights,
then link the full changelog.

Numbers over adjectives. A list of merged commit subjects is a merge log
wearing a release-note hat. Put the hand-written highlights above it.

Versions are PEP 440 identifiers. Semantic-versioning meaning applies to
the documented public API — including `doctest_docutils`'s CLI arguments,
the `pytest11` entry point, `linkify_issues`' `conf.py` keys, and the
registered doctest flags, not only imported Python symbols. gp-libs is
pre-1.0: a minor version bump may still include a breaking change.

## Docstrings

New public functions and methods carry a doctest that exercises them —
doctests are both documentation and a test, and gp-libs is the tool that
runs them. This guides new work; not every existing function conforms
today, and fixing that opportunistically is welcome but is not a
prerequisite for an unrelated change.

The prime directive: never restate the type. The annotation is the source
of truth; the docstring carries what the annotation cannot.

This is documentation debt wearing a docstring:

    def get_test_name(node: Node) -> str:
        """Get the test's name.

        Parameters
        ----------
        node : Node
            The node.

        Returns
        -------
        str
            The name.
        """

Document instead the dimensions the type system cannot encode:

- **Mutation.** What it changes in place.
- **Ownership.** What the caller must close, release, or keep alive.
- **Ordering.** Whether results come back in a guaranteed order.
- **Timing.** What has finished by the time the call returns.
- **Failure.** Which exceptions are raised and what triggers each.
- **Idempotence.** Whether calling twice does anything the second time.
- **Concurrency.** Whether calls are coalesced, queued, or independent.
- **Units and ranges.** What a number means and what values are accepted.
- **Boundary behaviour.** What zero, empty, and the maximum do.
- **Platform.** Behaviour that differs by docutils or myst-parser version.
- **Security boundary.** What is executed, and what is only read.

Follow [NumPy docstring style](https://numpydoc.readthedocs.io/en/latest/format.html)
for every public function, method, and class — enforced by ruff's
`pydocstyle` rules (`convention = "numpy"` in `pyproject.toml`), not
relitigated in review. The first sentence stands alone; tooling truncates
there. PEP 257 applies: triple double quotes, an imperative one-line
summary ending in a period, a blank line before any extended description.
Do not repeat an introspectable signature.

**Classes with fields** — `NamedTuple`, dataclasses — document every field
in an `Attributes` section:

```python
class ConsoleExample(t.NamedTuple):
    """Console example collected from a Markdown page.

    Attributes
    ----------
    path : pathlib.Path
        Markdown file the example was collected from.
    """
```

Autodoc renders every field whether or not you describe it, so an
undocumented `NamedTuple` field ships to the API docs as "Alias for field
number 0" and a dataclass field ships bare. Document all of them — a class
with three fields and two documented still ships a stub for the third.

## Logging

These rules guide future logging changes; existing code may not yet
conform.

**Logger setup.** Use `logging.getLogger(__name__)` in every module. Add a
`NullHandler` in library `__init__.py` files. Never configure handlers,
levels, or formatters in library code — that is the application's job.

**Structured context via `extra`.** Pass structured data on every log call
where useful for filtering, searching, or test assertions.

Core keys (stable, scalar, safe at any log level):

| Key | Type | Context |
|-----|------|---------|
| `doctest_source_file` | `str` | doctest source path (`.rst`, `.md`, `.py`) |
| `doctest_block_type` | `str` | block type (`doctest_block`, code fence) |
| `sphinx_extension` | `str` | Sphinx extension name |

Treat established keys as compatibility-sensitive — downstream users may
build dashboards and alerts on them. Change deliberately. Keys are
`snake_case`, not dotted, with project-specific prefixes (`doctest_`,
`sphinx_`). Prefer stable scalars; avoid ad-hoc objects.

**Lazy formatting.** `logger.debug("msg %s", val)`, not f-strings. Two
reasons: deferred string interpolation is skipped entirely when the level
is filtered, and aggregators group by message template — `"Running %s"` is
one signature grouped ×10,000, while f-strings make every line unique.
When computing `val` itself is expensive, guard with
`if logger.isEnabledFor(logging.DEBUG)`.

**`stacklevel` for wrappers.** Increment for each wrapper layer so
`%(filename)s:%(lineno)d` and OTel `code.filepath` point to the real
caller. Verify whenever call depth changes.

**Log levels.**

| Level | Use for | Examples |
|-------|---------|----------|
| `DEBUG` | Internal mechanics | Doctest parsing, node traversal steps |
| `INFO` | Lifecycle, user-visible operations | Extension loaded, document processed |
| `WARNING` | Recoverable issues, deprecation | Deprecated directive, missing optional dependency |
| `ERROR` | Failures that stop an operation | Parse error, invalid configuration |

**Message style.** Lowercase, past tense for events: "extension loaded",
"parse error". No trailing punctuation. Keep messages short; put details
in `extra`, not the message string.

**Exception logging.** Use `logger.exception()` only inside `except`
blocks when not re-raising. Use `logger.error(..., exc_info=True)` when
the traceback is needed outside an `except` block. Avoid
`logger.exception()` followed by `raise` — it duplicates the traceback.
Either add context via `extra` that would otherwise be lost, or let the
exception propagate.

**Testing logs.** Assert on `caplog.records` attributes, not string
matching on `caplog.text`. Scope capture with
`caplog.at_level(logging.DEBUG, logger="doctest_docutils")`. Filter
records rather than index by position. Assert on schema
(`record.sphinx_extension == "doctest_docutils"`), not substring matching.
`caplog.record_tuples` cannot access extra fields — always use
`caplog.records`.

**Avoid:** f-strings or `.format()` in log calls; unguarded logging in hot
loops; catch-log-reraise without adding new context; `print()` for
diagnostics; logging secret environment variable values (log key names
only); non-scalar ad-hoc objects in `extra`; custom `extra` fields
referenced in format strings without safe defaults (a missing key raises
`KeyError`).

## Source comments

A comment ships only if it passes all three gates. Fail any: delete or
rewrite. Borderline: delete — borderline means the information is
reconstructible, which is what makes deletion cheap.

**Loss.** Three years from now, would losing this cost a maintainer real
time rediscovering intent, an invariant, a constraint, or a failure mode
the code and tests do not already make obvious?

**Elite.** Would SQLite, Redis, the Go standard library, or CPython write
this comment, at this length? Those projects state the constraint and
stop. They do not argue with an imagined objector.

**Upkeep.** Will it stay true without maintenance? A comment that
hand-syncs a value the code owns — a count, an offset, a line reference, a
duplicated constant — is false the first time that value moves.

### Ceiling

One or two lines. A comment reaching four is either carrying several
facts, in which case split it, or arguing, in which case cut it to the
fact.

Rationale, alternatives weighed, and the story of how the code got here
belong in the commit message: timestamped, attached to the exact diff, and
free to maintain.

### Keep

- Why over how: upstream quirks, protocol and compatibility constraints,
  performance tradeoffs still part of the contract.
- Invariants, preconditions, ordering, lifetime, and concurrency
  requirements that types and tests cannot express.
- Code that looks wrong but is not, so a later cleanup does not
  reintroduce the bug.
- A high-level sketch of an algorithm whose local operations do not
  reveal the whole.

### Delete

- Narration of the next lines; code translated into English.
- Restated names, types, defaults, or control flow.
- Values duplicated from the code and hand-synced.
- Justification, hedging, or apology for a choice.
- Speculation about future requirements.
- History version control already holds, including commented-out code.
- Ticket and issue numbers. They say nothing to a reader without tracker
  access, and they rot when the tracker moves. Unfinished work goes in the
  tracker, not the source.
- Transient observations — "currently", "for now", "the latest release" —
  that go stale with no nearby edit.

### The upkeep gate in practice

It reaches values that track our own code. It does not reach frozen
external facts.

Bad (Delete):

```python
# There are 321 tests to complete for servers.
```

Good (Keep):

```python
# CPython < 3.11 has no ExceptionGroup, so this branch stays.
```

### Documentation exception

Doctests, minimal usage examples, and `Parameters`/`Returns`/`Attributes`
entries on public API are exempt from the loss gate — they serve the
caller, not the maintainer. They are exempt from nothing else. Ceiling: a
good man page entry. Autodoc ships every `NamedTuple` or dataclass field
whether or not you describe it, and a doctest that runs is also a test.

## Terminology and capitalization

Pick the domain noun and keep it. This project's own vocabulary is
`doctest_docutils` (the module), `pytest_doctest_docutils` (the plugin),
and `linkify_issues` (the Sphinx extension) — do not call the finder a
"scanner" in one paragraph and a "collector" in the next, and do not
alternate "issue link" with "reference link" once `linkify_issues` has
established the term.

Stable vocabulary is what makes search, deep links, and an agent's
retrieval work at all.

Python and PyPI keep their own capitalisation. Distribution names are
written as they are published.

Do not write counts into prose — how many symbols exist, how many tests
there are. They go stale silently and no reader needs them. Counts that
pin a fixture or guard an invariant are different, and belong in code.

## Cross-references

Point the advanced reader at the deep-dive rather than inlining it, and
put the link where their interest peaks — on the phrase that made them
curious ("how the finder decides", "the docutils machinery") — not as a
standalone footnote the eye skips. Use `{class}`, `{meth}`, `{func}`,
`{mod}`, `{exc}`, `{attr}` for API objects; `{ref}` or `{doc}` for
documentation pages and section anchors; a Markdown link or reference link
for external projects. A `{ref}` must match its target's anchor exactly —
anchors mix underscore and hyphen forms across pages (`doctest_docutils`,
`linkify-issues`).

Link the first prose mention of any symbol that has a useful destination
on that page. After the first linked mention, later mentions can stay
plain unless the distance or context makes another link useful. Do not
rely on a later reference section to satisfy the first-mention rule. If
the first occurrence would be a heading, grid-card teaser, or introductory
sentence, link that occurrence or retitle the heading so the first prose
mention can carry the link. Leave command examples, code blocks, and
literal configuration values as code; link the surrounding prose instead.

`just build-docs` catches a broken cross-reference; the doctests do not —
build the docs before you commit a page with a `{ref}` or `{doc}` role on
it.

## Markdown

Prose wraps at 80 columns. Table rows, badge lines, and long links are
exempt, because breaking them harms rendering. A pull request or issue
body does not wrap at all: GitHub renders a single newline as a space in a
file and as a line break in a comment, so a wrapped comment body arrives
as ragged stubs.

GitHub alert blocks — `> [!NOTE]`, `> [!WARNING]` — render as literal text
outside GitHub, so reserve them for at most one load-bearing warning per
document. Write the sentence so it carries the fact on its own, and a
renderer that drops the marker loses nothing.

Do not use a local absolute path or an email address in anything
published.

## Code blocks

Code blocks are paste-and-run units: pasting one block runs exactly one
intended action. Executed examples are exempt — the test suite runs them,
nobody pastes them.

- **One command per block.** Multiple steps may share a block only when
  explicitly chained with `&&`, `;`, or `\` continuations — the chain is
  then one logical command.
- **Explanations go in prose above the block**, never as `#` comments
  inside it.
- **Command menus are per-command blocks with prose lead-ins**, not
  tables.
- **Shell commands use the `console` tag with a `$ ` prefix.** This
  separates interactive commands from scripts and enables prompt-aware
  copy.
- **Split long commands with `\`** — one flag or flag+value pair per
  indented continuation line, positional arguments last.

Good — show the last ten commits as a graph:

```console
$ git log \
    --max-count=10 \
    --graph \
    --oneline
```

Bad:

```console
# Show the last ten commits as a graph
$ git log --max-count=10 --graph --oneline
```

## Commits

```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific technical changes made
- Focused on a single topic
```

Keep the subject to 50 characters or fewer, excluding any trailing
`(#NN)` pull request reference, and wrap body lines at 72. Separate the
`why:` and `what:` blocks with a blank line.

Routine maintenance commits drop the colon and take a capitalised
description, which is what distinguishes them at a glance in
`git log --oneline`:

```
py(deps[dev]) Bump dev packages
ai(rules[AGENTS]) Judge comments by three gates
```

Everything that changes behaviour keeps the colon.

Common types: **feat**, **fix**, **refactor**, **docs**, **chore**,
**test**, **style**, **ci**, **py(deps)**, **py(deps[dev])**,
**ai(rules[AGENTS])**, **ai(claude[rules])**, **ai(claude[command])**.

Example:

```
doctest_docutils(feat[parse]): Add support for myst-parser code blocks

why: Enable doctest execution in Markdown documentation files

what:
- Add detection for ```{doctest} fence syntax
- Register myst directives automatically
- Add tests for Markdown doctest parsing
```

For a multi-line message, use a heredoc so the formatting survives:

```console
$ git commit -m "$(cat <<'EOF'
Scope(feat[detail]): Concise description

why: Explanation of the change.

what:
- First change
- Second change
EOF
)"
```

### Release commits

Never create tags. Never push tags. The owner handles tagging and tag
pushes, because a tag triggers the publish workflow.

A release commit subject is plain and short: `Tag v<version>`. The
detailed why and what go in the body. Do not use the
`Scope(type[detail]):` format for a release — it buries the lede.

## Slop prevention

Treat AI slop as review-hostile noise, not as proof that text or code is
wrong. The goal is to maximise information density.

- **AI signatures.** No "Generated by", no conversational filler, no
  unexplained emoji, no tool metadata.
- **Brittle references.** No hard-coded line numbers, fragile file
  counts, dated "as of" claims, bare SHAs, or local absolute paths —
  unless they are strict evidentiary artefacts such as a benchmark log.
- **Diff narration.** Do not restate what moved, was renamed, or was
  removed in anything the reader holds alongside the diff: code,
  docstrings, README, CHANGES, or a pull request description. The diff
  and commit message already carry it.
- **Branch-internal narrative.** Do not mention intermediate states,
  abandoned approaches, or "no longer" behaviour unless users of a
  published release actually experienced the old state (the
  published-release test below).
- **Low-value scaffolding.** No ownerless TODOs, unused future-proofing,
  debug artefacts, or defensive wrappers around failure modes nothing can
  reach.
- **Prose inflation.** The diction table under [Voice](#voice) governs;
  replace an inflated word with a concrete description of behaviour,
  constraints, or trade-offs.
- **Coded labels.** Write rules and findings as plain imperatives. No
  `[R1]`, `Option B`, or any index a reader has to decode in shipped
  text. Internal agent bookkeeping may use ids; shipped text may not.

Preserve the "why". Never delete a comment documenting an invariant, a
protocol constraint, a platform quirk, or an upstream workaround — those
are the facts [Source comments](#source-comments) keeps, and every other
comment is judged by it. Preserve exact counts, dates, and SHAs when they
serve as evidence in benchmark results, release notes, or lockfiles.

### Durable source links

Link to a pinned revision, never to trunk. A pinned permalink is not a
brittle reference; an unlinked SHA dropped into prose is. `blob/master/…`
links rot silently — the file moves, lines shift, and the anchor lands on
unrelated code while still resolving.

- Prefer a release tag (`blob/v0.0.19/…`). Most durable, and it tells the
  reader which released version the claim held for.
- Otherwise use a 7-char commit ref (`blob/9a29b1a/…`) reachable from
  trunk. Use when there is no tag or the claim is about unreleased code.
  Never a PR-head SHA — it can be rebased or garbage-collected.
- Reserve `blob/master/…` for living documents meant to always show the
  latest state, such as this file and `CONTRIBUTING.md`.
- Line anchors (`#L120-L145`) are only safe on a pinned ref.

### The published-release test

Long-running branches accumulate tactical decisions — renames, refactors,
attempts-then-reverts. When deciding what counts as branch-internal, use
trunk or the parent branch as the baseline — not intermediate states
inside the current branch. Ask: did users of the most recently published
release ever experience this old name, old behaviour, or bug? If no, it
is branch-internal narrative — move it to the commit message and describe
only the final state in the artefact.

Keep in shipped artefacts: deprecations and migration guides for symbols
that actually shipped; `### Fixes` entries for bugs that affected users of
a published release; comments explaining why the current code looks this
way that make sense to a reader who never saw the previous version.

### Cleanup in hindsight

When applying these rules retroactively from inside a feature branch,
first establish scope by diffing against the parent branch or trunk to
identify which commits this branch actually introduced. For in-branch
commits, prefer `fixup!` commits with `git rebase --autosquash` to address
each causal commit at its source, or a single cleanup commit at branch
tip. Default to leaving trunk or parent-branch commits alone; act on them
only on explicit instruction, and fold any resulting cleanup into a single
commit at branch tip rather than rewriting shared history.
