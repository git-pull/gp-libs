(pytest_doctest_docutils-examples)=

# Examples

## Markdown file

Run a Markdown documentation file directly:

```console
$ pytest README.md
```

## Documentation directory

Run every collected documentation doctest under `docs/`:

```console
$ pytest docs/
```

## Python modules

Collect Python-module doctests through gp-libs' plugin:

```console
$ py.test src/ --doctest-docutils-modules
```

The module flag is opt-in so documentation files stay the default path for this
plugin.
