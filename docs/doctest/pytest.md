# pytest plugin

:::{note}

This plugin disables pytest's standard `doctest` plugin.

:::

The pytest plugin is built on top of the doctest_docutils module, which is in
turn compatible with {mod}`doctest`.

## Markdown

If you install [myst-parser], doctest will run on .md files.

```console
$ pytest README.md
```

[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

## API

```{eval-rst}
.. automodule:: pytest_doctest_docutils
   :members:
   :show-inheritance:
   :undoc-members:
```
