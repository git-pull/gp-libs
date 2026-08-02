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

One name a group cannot take is the one the page would generate for a block that
declares none — the page's own name at `--namespace-scope document`, the page and
the block's position at the default. Both would answer to one namespace and one
node id, so a page spelling both stops with
{exc}`~doctest_docutils.NamespaceNameCollisionError` rather than merging them.
Rename the group; a page whose every block names one generates nothing to collide
with, so `.. doctest:: README.md` on such a page is only a style choice.

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

## Write a block a reader is meant to paste

A `>>>` prompt is for a session a reader reads. When the block is there to be
copied into a file, the prompt is in the way, and an expected-output line beneath
it puts an assertion into whatever the reader pasted. Such a page carries no
prompt at all — and a finder that goes looking for `>>>` cannot see it.

Write those blocks as `{testcode}`, the directive {mod}`sphinx.ext.doctest`
defines. The body is plain Python, run the way a module body runs, so it takes as
many statements as it likes and a bare expression on the last line prints
nothing:

```{testcode}
greeting = "hello"
shouted = greeting.upper()
```

A `{testcode}` expects to print nothing. When it does print, say what with a
`{testoutput}` block under it:

```{testcode}
print(shouted)
```

```{testoutput}
HELLO
```

The two blocks above share a namespace, so the second reads what the first bound.
A `{testcode}` that names no group is named for its page, because sharing the
page is the whole point of the form — a visible block and the hidden one
asserting on it have to meet somewhere. Name a group as the directive's
argument, `{testcode} intro`, to keep two runs on one page apart.

A `>>>` block is named for its page only where the scope above says so. So at
`--namespace-scope document` the two forms land in the same namespace and read
each other's names, and at the default they do not. Write a page that mixes them
at document scope, or keep each page to one form.

A page written this way sets up the same way, with no prompt:

````markdown
```{testsetup}
base = 40
```
````

A `{testsetup}` and `{testcleanup}` may still be written with prompts, which is
how the rest of these docs write them; the prompt decides how the body is read.
A page holding a `{testcode}` names its unnamed setup for the page too, so the
setup a prompt-free page writes reaches the code it is for.

That is what lets a page assert without showing its assertions. Mark a block
`:hide:` and it runs while every builder drops it, so the reader meets only the
block written to be pasted:

````markdown
```{testcode}
:hide:

assert shouted == "HELLO"
```
````

```{testcode}
:hide:

assert shouted == "HELLO"
```

The page you are reading has that hidden block in it, immediately above.

`{testoutput}` takes `:options:` for the doctest flags the comparison runs under,
and both directives take `:skipif:`. `:pyversion:` parses, because Sphinx
declares it here, but neither Sphinx nor this runner acts on it outside
`{doctest}` — the page says so when you use it. Guard a block with `:skipif:`
instead.

The cost of the prompt-free form is that there is no interleaving: one block is
one example, so a `{testoutput}` says what the block prints in total rather than
what any line in it prints. A failure quotes the block entire, so the reader sees
where they are.

## Compare with stdlib doctest

Use the stdlib command when you are checking Python modules or plain text that
does not need docutils parsing:

```console
$ python -m doctest --help
```

Use {mod}`doctest_docutils` when the examples live inside Markdown or
reStructuredText structure that {mod}`doctest` would otherwise treat as plain
text.
