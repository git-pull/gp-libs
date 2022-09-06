(pytest_plugin)=
(pytest_doctest_docutils)=

# pytest plugin

:::{note}

This plugin disables {ref}`pytest's standard doctest plugin <pytest:doctest>`.

:::

The pytest plugin is built on top of the {ref}`doctest_docutils` module, which is in
turn compatible with {mod}`doctest`.

## Markdown

If you install [myst-parser], doctest will run on .md files.

```console
$ pytest README.md
```

[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

## Scanning python files

You can retain {ref}`pytest's standard doctest plugin <pytest:doctest>` of
running doctests in `.py` by passing `--doctest-docutils-modules`:

```console
$ py.test src/ --doctest-docutils-modules
```

You can disable it via `--no-doctest-docutils-modules`:

```console
$ py.test src/ --no-doctest-docutils-modules
```

## API

```{eval-rst}
.. automodule:: pytest_doctest_docutils
   :members:
   :show-inheritance:
   :undoc-members:
```
