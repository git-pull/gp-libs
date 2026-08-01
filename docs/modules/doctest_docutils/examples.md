(doctest_docutils-examples)=

# Examples

The docs test suite executes the prompt examples on this page. That keeps the
examples aligned with {class}`doctest_docutils.DocutilsDocTestFinder`.

## Markdown prompt block

```python
>>> import doctest_docutils
>>> finder = doctest_docutils.DocutilsDocTestFinder()
>>> source = "```python\n>>> 2 + 2\n4\n```\n"
>>> tests = finder.find(source, "example.md")
>>> len(tests)
1
```

## MyST doctest directive

```{doctest}
>>> sorted({"rst", "md"})
['md', 'rst']
```

A directive keeps a reader's view of the example clean: the rendered page drops
the `# doctest: +NORMALIZE_WHITESPACE` written below, while the run still
applies it, so the two spaces in the printed output match the one below them.

```{doctest}
>>> print("a  b")  # doctest: +NORMALIZE_WHITESPACE
a b
```

## Blocks that share a namespace

Blocks naming the same group collect as one test, so the second reads what the
first bound:

```python
>>> import doctest_docutils
>>> finder = doctest_docutils.DocutilsDocTestFinder()
>>> source = (
...     "```{doctest} intro\n>>> greeting = 'hello'\n```\n"
...     "\nProse between the blocks.\n\n"
...     "```{doctest} intro\n>>> greeting.upper()\n'HELLO'\n```\n"
... )
>>> tests = finder.find(source, "example.md")
>>> [(test.name, len(test.examples)) for test in tests]
[('intro', 2)]
```

Blocks naming no group keep a namespace each, until you ask for the page:

```python
>>> import doctest_docutils
>>> page = "```python\n>>> alone = 1\n```\n\n```python\n>>> alone\n1\n```\n"
>>> apart = doctest_docutils.DocutilsDocTestFinder()
>>> [test.name for test in apart.find(page, "example.md")]
['example.md[0]', 'example.md[1]']
>>> shared = doctest_docutils.DocutilsDocTestFinder(namespace_scope="document")
>>> [test.name for test in shared.find(page, "example.md")]
['example.md']
```

## Finder result names

{class}`~doctest_docutils.DocutilsDocTestFinder` names collected examples with
the file path you pass in:

```python
>>> import doctest_docutils
>>> finder = doctest_docutils.DocutilsDocTestFinder()
>>> [test.name for test in finder.find(">>> 'docs'\n'docs'\n", "guide.rst")]
['guide.rst[0]']
```
