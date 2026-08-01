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
  examples after it unless you pass `--doctest-continue-on-failure`.
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
