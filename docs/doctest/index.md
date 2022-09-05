(doctest_docutils)=
(doctest_docutils_module)=

# Doctest w/ docutils

Built on {mod}`doctest`.

:::{note}

Before you begin, acquaint yourself with:

- {mod}`doctest`

  - normal usage via:

    ```console
    $ python -m doctest [file]
    ```

- Know what [docutils] does: parses reStructuredText (.rst). With the helper of [myst-parser], it also parses markdown (.md)

:::

## reStructuredText

```console
$ python -m doctest_docutils README.rst
```

That's what `doctest` does by design. Pass `-v` for verbose output.

## Markdown

If you install [myst-parser], doctest will run on .md files.

```console
$ python -m doctest_docutils README.md
```

As with the reST example above, no output.

```{toctree}
:hidden:

pytest
```

[docutils]: https://www.docutils.org/

## Internals

:::{note}

To get a deeper understanding, dig into:

- {mod}`doctest`

  - All console arguments by seeing the help command:

    ```console
    $ python -m doctest --help
    ```

  - data structures, e.g. {class}`doctest.DocTest`

    - source code: https://github.com/python/cpython/blob/3.11/Lib/doctest.py
    - documentation: https://docs.python.org/3/library/doctest.html

  - typings: https://github.com/python/typeshed/blob/master/stdlib/doctest.pyi

- [docutils]: which parses reStructuredText (.rst) and markdown (.md, with the
  help of [myst-parser])

:::

## API

```{eval-rst}
.. automodule:: doctest_docutils
   :members:
   :show-inheritance:
   :undoc-members:
```
