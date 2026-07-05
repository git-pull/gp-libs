(doctest_docutils)=
(doctest_docutils_module)=

# Documentation Doctests

{mod}`doctest_docutils` runs Python {mod}`doctest` examples from
documentation files. It parses reStructuredText through [docutils] and
Markdown through [myst-parser], then collects the examples the same way a
reader sees them in the page.

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} pytest plugin
:link: pytest
:link-type: doc
Run doctests in `.rst` and `.md` files via pytest.
:::

::::

## reStructuredText

Run the command against a reStructuredText file:

```console
$ python -m doctest_docutils README.rst
```

No output means the examples passed. Pass `-v` for verbose output.

## Markdown

Install [myst-parser] when you want the same collection behavior for Markdown:

```console
$ python -m doctest_docutils README.md
```

No output means the Markdown examples passed too.

```{toctree}
:hidden:

pytest
```

[docutils]: https://www.docutils.org/
[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

## Internals

:::{note}

For the rarer cases where you need the lower layers, start with:

- {mod}`doctest`

  - Command-line options:

    ```console
    $ python -m doctest --help
    ```

  - Data structures such as {class}`doctest.DocTest`

- [docutils], which parses reStructuredText
- [myst-parser], which lets docutils parse Markdown

:::

## API

```{eval-rst}
.. automodule:: doctest_docutils
   :members:
   :show-inheritance:
   :undoc-members:
```
