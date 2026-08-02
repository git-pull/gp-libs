(pytest_doctest_docutils-how-to)=

# How-to

## Run documentation files

Run one Markdown file:

```console
$ pytest README.md
```

Run a directory:

```console
$ pytest docs/
```

## Include Python module doctests

Use `--doctest-docutils-modules` when you also want this plugin to collect
Python-module doctests:

```console
$ py.test src/ --doctest-docutils-modules
```

Disable Python-module collection explicitly with
`--no-doctest-docutils-modules`:

```console
$ py.test src/ --no-doctest-docutils-modules
```

## Let a page build one example across several blocks

Every block on a page runs against a namespace of its own. A name bound in one
block is gone by the next, which is what lets a reader copy any single block out
of the page and run it. Most pages want that, and it is what you get with no
configuration at all.

A narrative page often wants the opposite: the prose walks through one session a
piece at a time. Name a group on the blocks that belong together, as the
directive's argument:

````markdown
```{doctest} intro
>>> greeting = "hello"
```

Prose between the two blocks.

```{doctest} intro
>>> greeting.upper()
'HELLO'
```
````

reStructuredText names a group the same way:

```rst
.. doctest:: intro

    >>> greeting = "hello"
```

A group collects as one item — `page.md::intro` — holding every block that named
it, in page order. A group reaches as far as the page it is written on: the same
name on a second page is a second namespace.

A block can name several groups at once, comma separated, and joins each of
them — it runs once per group, against that group's namespace. `*` stands for
every group the page declares, which is how you write one setup for all of them:

```rst
.. testsetup:: *

    >>> import math
```

`.. testsetup::` and `.. testcleanup::` run before and after the rest of their
group whatever order the page writes them in, so you can move them out of a
reader's way. Their output is still checked, unlike in Sphinx, so a setup that
raises is reported rather than swallowed. A failing example ends its namespace,
which means that namespace's cleanup does not run.

Only the directive form can name a group. A plain ```` ```python ```` fence, a
bare fence, an indented block, and a reStructuredText doctest block have nowhere
to write one. To share state between those, widen the page for a single run:

```console
$ pytest docs/ --doctest-docutils-namespace-scope=document
```

Or settle it for the project:

```ini
[pytest]
doctest_docutils_namespace_scope = document
```

Under `document`, the blocks that name no group share one namespace per page,
named for the page. Named groups still partition it — declaring a group is the
author asking for sharing, so a group is its own namespace at either setting.

### What sharing costs

A namespace is one item. That is what keeps a shared page correct under
`pytest -n auto`: no worker is ever handed half of a session. It also means:

- The namespace passes or fails as a single line, and a failure stops the
  examples after it unless you pass `--doctest-continue-on-failure`. Stopping
  is what keeps a half-built namespace out of the blocks below: they never run.
  With `--doctest-continue-on-failure` they do run, against a namespace missing
  whatever the failed example would have bound, so one broken line can report
  as a first failure followed by a run of {exc}`NameError`s that are not
  independent.
- A function-scoped fixture sets up once per namespace instead of once per
  block. A page whose blocks each expect a fresh fixture belongs at `block`.
  A block gated end to end is the exception: it is its own item, and it is
  marked skipped before setup, so it neither shares that setup nor pays for
  one of its own.
- A block whose every example is skipped is the one thing a namespace does not
  hold. It binds nothing the other blocks could read, so it is lifted back out
  and collects as an item of its own — `page.rst::intro[1]` — and still
  reports `SKIPPED`. The page collects one item more than it has namespaces
  for each such block, which is one more line in `--collect-only` and one more
  entry in a JUnit report.
- The report's numbered gutter spans the whole namespace, so the prose between
  two blocks shows up as blank numbered lines above the failing prompt.

One page shape moves further. docutils numbers a bare reStructuredText doctest
block by its *last* line, so that block's examples report lines below where it
sits whether or not it shares anything. Sharing extends the reach of that: a
block written close underneath one is pushed past it, by as many lines as the
two overlap. The gutter still ends on the failing prompt. Write those blocks as
`.. doctest::` directives when the exact line matters — a directive is numbered
by the line it opens on.

### Keep a node id for every block

The item a namespace collects as is the thing you can point pytest at. When a
namespace is one item, that reach stops at the page: `--lf` re-runs the whole
page rather than the block that failed, `-k` and `--deselect` cannot single a
block out, a JUnit report names the page, and there is no id to paste back
while you iterate on one block.

Those reaches are worth most where each block has a namespace of its own, the
default scope. A block that reads what an earlier one bound is a fragment of a
session, so selecting it alone — by id, by `-k`, or by `--lf` after it failed —
runs it without the block it depends on. See
{ref}`what per-block items cost <pytest_doctest_docutils-per-block-costs>`.

Take the other trade when you want those, and a fixture per block, more than
you want the single line:

```console
$ pytest docs/ --doctest-docutils-namespace-items=per-block
```

Or settle it for the project:

```ini
[pytest]
doctest_docutils_namespace_items = per-block
```

Every block is an item again, under the id it carries when nothing is shared —
`page.md::page.md[1]`, or `page.rst::intro[1]` inside a group — and the blocks
of one namespace are handed the *same* globals rather than a copy each. A
function-scoped fixture is back to setting up once per block, which is what a
project promising a fresh fixture for every example needs.

The two settings answer different questions, and both still apply: the scope
says what shares a namespace, this one says whether sharing costs the blocks
their ids. At the default scope no page state is shared either way — but
selecting `per-block` is still the opt-in to a live shared mapping, because a
page that declares a group shares one whatever the scope.

A run that keeps a node id for every block says so in its header, so you can
tell from the report which one you got. The scope rides along on the same line:

```text
doctest-docutils: namespace items: per-block, namespace scope: document
```

A run that only widens the scope is not announced; the default layout reports
nothing, so the header of a project that never touched this setting reads as it
always has.

(pytest_doctest_docutils-per-block-costs)=

### What per-block items cost

A live namespace is a Python object, so it neither crosses a process boundary
nor outlives the fixtures that filled it. The cost shows up in five places.

Under `pytest-xdist`, two blocks of one namespace landing on different workers
would leave the second reading a namespace the first never built. Which
scheduler you get decides whether that can happen, and `-n` on its own does not
choose one: `pytest-xdist` fills it in with `--dist load`, which distributes by
item.

So the plugin fills it in first, with file-level scheduling. `pytest docs/ -n
auto` keeps every page on one worker and your shared pages pass:

```console
$ pytest docs/ -n auto
```

Nothing about the run changes otherwise — the node ids stay the ones the layout
collects, and `-v` names the scheduler that ran if you want to see it. File
level is as fine-grained as this can go. `loadgroup` would suit the
`xdist_group` marker the plugin emits per namespace, but that group reaches a
scheduler through a node-id suffix the *worker* writes, from the worker's own
`--dist` value, so no substitute made on the controller can use it.

Name a scheduler yourself and it is yours. `--dist loadfile`, `--dist
loadgroup`, `--dist loadscope` and `--dist each` all keep a namespace whole,
and `loadgroup` is the finer grained of the two obvious ones: `loadfile` pins a
whole file to one worker, while the group is the file plus the namespace, so a
page holding several namespaces still spreads.

```console
$ pytest docs/ -n auto --dist loadgroup
```

Ask for `--dist load` or `--dist worksteal` — by flag or through `addopts` —
and the session stops instead, naming the page it would have split. Overruling
a scheduler you asked for by name would be the plugin deciding it knows better;
reporting a page that is only wrong because of how it was scheduled would be
worse:

```text
ERROR: doctest_docutils_namespace_items = per-block can hand a namespace's
blocks one globals mapping between them — a page declaring a group does,
whatever the scope — and a mapping cannot cross processes. --dist worksteal
hands a file's items to whichever worker is free, so it can send docs/page.md's
blocks to different workers. Run with --dist loadgroup or --dist loadfile, or
set doctest_docutils_namespace_items = merged. Dropping --dist leaves -n free
to keep each page on one worker.
```

That reads the run, not the setting. A run holding no page whose blocks split —
a suite of Python tests, a single-block page, `--collect-only`, one worker —
keeps its workers whatever it asked for, so carrying the layout in your ini
never costs `-n` to a session that has no namespace to protect.

A test-retry plugin repeats a single item, which a live namespace cannot
survive. Under `merged` a retry re-runs the namespace from its first block, so
the run rebuilds what it needs and a real failure stays a failure. Under
`per-block` the retry re-runs only the block that failed, against the mapping
that block already changed — so an example whose expectation happens to come
true on the second attempt would be reported as a pass. There is no way to
rebuild the namespace for one block, so the repeat is refused instead:

```text
Failed: page.rst::demo[1] was run twice against a namespace laid out per
block. A repeated block runs against the globals it already changed, so its
result cannot be trusted. Drop --reruns (and anything else that repeats an
item), or set doctest_docutils_namespace_items = merged, which re-runs a
namespace from its first block.
```

A block that passes first time is never repeated, so a green run under
`--reruns` is unaffected.

Running one block by its id has the same shape: `pytest page.md::page.md[1]`
runs that block and nothing else, so a block reading a name an earlier one
bound reports the `NameError` it earns. `-k`, `--deselect` and `--lf`
reach a block the same way and cost the same thing — a `--lf` re-run of a
failure in a shared page reports the missing binding rather than the diff you
were chasing. That is inherent to running a fragment of a session, not
something the setting can hide.

A namespace shares the mapping, not the lifetime of what a fixture put in it.
Each block is its own item, so a function-scoped fixture tears down between
blocks. The name that fixture fills is rebound fresh for the next block, but a
name a block derived from it is not: it still holds the finalized object, and a
finalized object usually answers rather than raising. A page reads a plausible
wrong value — a cached attribute that looks right beside a connection that is
already closed — with nothing in the report to say so.

Give a fixture a page carries across its blocks `scope="module"`. A page is
what module scope means here — the collector for a `.md` or `.rst` page is a
{class}`pytest.Module`, as pytest's own text-doctest collector is — so the
fixture sets up once for the page and tears down when the page ends, and the
object a block saves stays the object the next block reads.

Name `module` rather than reaching for anything wider. `class` has no node to
attach to on a page, so it silently falls back to setting up per block, and
`package` anchors to the directory holding the `conftest.py` that *defines* the
fixture, and only when that directory is an importable package — a fixture
defined further up resolves to the whole run however the page's own directory
looks. Only `function`, `module` and `session` mean what they say here.

Two things follow from a page being a module for scope and nothing else. A
module-scoped fixture cannot request a function-scoped one, so reaching for
{ref}`tmp_path <pytest:tmp_path>` stops the page with pytest's `ScopeMismatch`
— ask for `tmp_path_factory` instead. And no
module object stands behind a page,
so `request.module` is `None`; a `conftest.py` shared with `.py` tests that
reads it works on those and breaks here. `request.path` names the page.

Across worker processes it is a page per worker, not a page per run. Leaving
`-n` unadorned keeps a page whole, and so does `--dist loadfile`; asking for
`--dist loadgroup` while every block is its own namespace groups by block
instead, which hands one page to two workers and sets the fixture up in each.

And because the blocks share one mapping, they share whatever lives in it —
including `__future__` flags, which {mod}`doctest` derives from the namespace at
run time. A `from __future__ import ...` in one block is in force for the rest
of its namespace.

## Set options for a whole block

A `{doctest}` directive can carry the flags its examples would otherwise repeat.
`:options:` takes the same names as the inline `# doctest:` comment, and an
example that writes its own flag wins over the directive's:

```rst
.. doctest::
    :options: +ELLIPSIS

    >>> print("hello world")
    hello ...
```

`:skipif:` skips a block on a condition the page works out for itself, so you
don't have to write `+SKIP` by hand for one interpreter or one platform. It
takes a Python expression, which is **evaluated** when the page is read, and a
true result marks the block `+SKIP`:

```rst
.. doctest::
    :skipif: sys.version_info < (3, 12)

    >>> "a modern interpreter"
    'a modern interpreter'
```

That is the same flag `:options: +SKIP` sets, so the two spellings report
alike: the block still collects, still counts, and still answers to its own
node id. The reason pytest prints is the one it prints for any skipped
example, which names the flag rather than your condition:

```console
$ pytest page.rst -rs
```

```text
SKIPPED [1] page.rst: page.rst:6: every example skipped
1 skipped
```

Where `:options:` sets defaults an example can override, a condition is a gate
it cannot: an example writing `# doctest: -SKIP` inside a gated block stays
skipped. Sphinx drops such a block before reading it at all, and an example that
could reopen it would run on exactly the interpreter or platform the condition
named. The expression sees `sys` and the globals the document starts
with, not anything the page's own examples bound — it is answered while the
page is being read, before any of them run. Naming anything else stops the page
with {exc}`~doctest_docutils.SkipifExpressionError`, which reports the file,
line, and expression to go fix.

Reading a page is all `--collect-only` does, so listing a page's items runs its
`:skipif:` expressions; keep them free of side effects.

Skipping one block of a group leaves the group's other blocks running, and the
skipped one still reports. Because a block with nothing left to run binds no
name the group could read, it does not need to share the group's item: it
collects as one of its own, named for the group and for the block's position on
the page, counted from zero across every doctest block. The second block of
`page.rst` in group `intro` is `page.rst::intro[1]`; on a page merged by
`--doctest-docutils-namespace-scope=document` it is `page.rst::page.rst[1]`,
which is the name that block already carries when every block keeps its own
namespace. So the node id a reader pastes back to pytest does not move with the
scope.

Two cases stay where they are. A block whose examples are only *partly*
skipped is not a skipped block — it has something left to run, and it reports
with its namespace like any other item. And when *every* block of a namespace
is gated, there is nothing for them to be silent beside: the namespace keeps
them all and reports skipped once, as one item, rather than once per block.

A skipped block is still parsed, so malformed doctest source in one reports
as an error rather than passing unnoticed — the same as for `:options: +SKIP`.

`:skipif:` works the same on `.. testsetup::` and `.. testcleanup::`, which
declare the option too.

## Hide a setup line from rendered docs

Mark a prompt line with `# doctest: +HIDE` when your suite should run it but a
reader shouldn't see it — a fixture import, a seed value, or a path you set up
before the example that matters:

```python
>>> secret = 40  # doctest: +HIDE
>>> secret + 2
42
```

The marker changes nothing about the run: the line still executes and its
output is still checked. It only tags the line so a documentation renderer can
drop it from the rendered page while pytest keeps testing it from source.

Importing {mod}`doctest_docutils` registers the marker, so `# doctest: +HIDE`
parses in `.rst`, `.md`, and Python-module doctests under pytest and under the
standalone `python -m doctest_docutils` command alike.

## Keep pytest's built-in doctest plugin disabled

The gp-libs plugin blocks pytest's built-in doctest plugin by default. Keep
`-p no:doctest` in local examples when you are demonstrating explicit pytest
configuration:

```ini
[pytest]
addopts = -p no:doctest
```
