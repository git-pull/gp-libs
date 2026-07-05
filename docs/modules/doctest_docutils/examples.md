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

## Finder result names

{class}`~doctest_docutils.DocutilsDocTestFinder` names collected examples with
the file path you pass in:

```python
>>> import doctest_docutils
>>> finder = doctest_docutils.DocutilsDocTestFinder()
>>> [test.name for test in finder.find(">>> 'docs'\n'docs'\n", "guide.rst")]
['guide.rst[0]']
```
