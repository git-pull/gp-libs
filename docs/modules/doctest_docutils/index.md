(doctest_docutils)=
(doctest_docutils_module)=

# doctest_docutils

{mod}`doctest_docutils` runs Python {mod}`doctest` examples from documentation
files. It parses reStructuredText through [docutils] and Markdown through
[myst-parser], then collects the examples a reader sees in the page.

Use this module when you want a direct command for a single documentation file.
Use {doc}`../pytest_doctest_docutils/index` when you want pytest collection,
fixtures, and suite-level reporting.

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Tutorial
:link: tutorial
:link-type: doc
Run your first documentation doctest from a Markdown page.
:::

:::{grid-item-card} How-to
:link: how-to
:link-type: doc
Choose files, run verbose output, and map the command to stdlib doctest.
:::

:::{grid-item-card} Examples
:link: examples
:link-type: doc
See the supported Markdown and reStructuredText example shapes.
:::

:::{grid-item-card} API Reference
:link: reference
:link-type: doc
Inspect finder, runner, directive, and CLI APIs.
:::

::::

## Default command

Run a Markdown page:

```console
$ python -m doctest_docutils README.md
```

No output means the examples passed. Add `-v` when you want the standard
doctest transcript.

```{toctree}
:hidden:

tutorial
how-to
examples
reference
```

[docutils]: https://www.docutils.org/
[myst-parser]: https://myst-parser.readthedocs.io/en/latest/
