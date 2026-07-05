(pytest_plugin)=
(pytest_doctest_docutils)=

# pytest_doctest_docutils

{mod}`pytest_doctest_docutils` lets [pytest] collect doctests from `.rst` and
`.md` files. Point pytest at a documentation file or directory, and the plugin
parses each page through {ref}`doctest_docutils` before pytest runs the
examples.

The plugin blocks {ref}`pytest's standard doctest plugin <pytest:doctest>` by
default so the same examples are not collected twice.

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Tutorial
:link: tutorial
:link-type: doc
Run documentation doctests through pytest.
:::

:::{grid-item-card} How-to
:link: how-to
:link-type: doc
Collect docs, Python modules, and option-flagged examples.
:::

:::{grid-item-card} Fixtures
:link: fixtures
:link-type: doc
Share setup through `doctest_namespace` and autouse fixtures.
:::

:::{grid-item-card} API Reference
:link: reference
:link-type: doc
Inspect collector, runner, and pytest hook APIs.
:::

::::

## Default command

Run documentation doctests under `docs/`:

```console
$ pytest docs/
```

```{toctree}
:hidden:

tutorial
how-to
fixtures
examples
reference
```

[pytest]: https://docs.pytest.org/en/stable/
