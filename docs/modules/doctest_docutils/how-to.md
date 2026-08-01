(doctest_docutils-how-to)=

# How-to

## Run a Markdown file

Use the module command with the file path:

```console
$ python -m doctest_docutils README.md
```

## Run a reStructuredText file

Use the same command for `.rst` files:

```console
$ python -m doctest_docutils README.rst
```

## See collected examples

Pass `-v` for verbose standard-library doctest output:

```console
$ python -m doctest_docutils README.md -v
```

## Let a page build one example across several blocks

Every block runs against a namespace of its own, so a name bound in one block is
gone by the next and any block can be run on its own. When a page is one session
told in pieces, widen the namespace to the whole page:

```console
$ python -m doctest_docutils README.md --namespace-scope document
```

Blocks that name a group share that group's namespace at either setting, because
naming a group is the author asking for it. A group is named as the directive's
argument, `.. doctest:: intro` in reStructuredText and its `{doctest} intro`
fence in Markdown. `--namespace-scope document` also pools the blocks that name
none.

Sharing costs you the guarantee that a block stands alone: a block that reads an
earlier binding fails when it is read, or run, by itself. See
{ref}`the pytest plugin's how-to <pytest_doctest_docutils-how-to>` for the same
choice under pytest, spelled `--doctest-docutils-namespace-scope` there, and for
what sharing costs a test run.

A shared page is reported as one item by default. Ask for one item per block,
each named for where the block sits, when you want to read the run block by
block:

```console
$ python -m doctest_docutils README.md --namespace-scope document --namespace-items per-block -v
```

A passing page prints nothing without `-v`. What changes without it is a
failure's heading, which names the block — `in README.md[1]` rather than
`in README.md`.

Nothing here schedules the blocks apart, so they share the namespace either way.
Under pytest they can be scheduled apart, which is what
{ref}`the plugin's how-to <pytest_doctest_docutils-how-to>` covers.

## Compare with stdlib doctest

Use the stdlib command when you are checking Python modules or plain text that
does not need docutils parsing:

```console
$ python -m doctest --help
```

Use {mod}`doctest_docutils` when the examples live inside Markdown or
reStructuredText structure that {mod}`doctest` would otherwise treat as plain
text.
