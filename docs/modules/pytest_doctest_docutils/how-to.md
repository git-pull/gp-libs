(pytest_doctest_docutils-how-to)=

# How-to

## Run documentation files

Run one Markdown file:

```console
$ pytest README.md
```

Run a directory:

```console
$ pytest docs/
```

## Include Python module doctests

Use `--doctest-docutils-modules` when you also want this plugin to collect
Python-module doctests:

```console
$ py.test src/ --doctest-docutils-modules
```

Disable Python-module collection explicitly with
`--no-doctest-docutils-modules`:

```console
$ py.test src/ --no-doctest-docutils-modules
```

## Keep pytest's built-in doctest plugin disabled

The gp-libs plugin blocks pytest's built-in doctest plugin by default. Keep
`-p no:doctest` in local examples when you are demonstrating explicit pytest
configuration:

```ini
[pytest]
addopts = -p no:doctest
```
