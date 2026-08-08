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

## Hide a setup line from rendered docs

Mark a prompt line with `# doctest: +HIDE` when your suite should run it but a
reader shouldn't see it — a fixture import, a seed value, or a path you set up
before the example that matters:

```python
>>> secret = 40  # doctest: +HIDE
>>> secret + 2
42
```

The marker changes nothing about the run: the line still executes and its
output is still checked. It only tags the line so a documentation renderer can
drop it from the rendered page while pytest keeps testing it from source.

The plugin registers the marker as pytest configures, so `# doctest: +HIDE`
parses in `.rst`, `.md`, and Python-module doctests. The standalone
`python -m doctest_docutils` command does not register it, so use the marker
when you run examples through pytest.

## Keep pytest's built-in doctest plugin enabled

This plugin composes with pytest's built-in doctest plugin. The built-in plugin
supplies `doctest_namespace`, output-checker extensions, report options, and
Python-module collection, while gp-libs owns the documentation-file collector.

Do not pass `-p no:doctest` when collecting documentation through gp-libs. If
the built-in plugin is disabled, collecting an affected documentation file or
using `--doctest-docutils-modules` raises a usage error instead of silently
collecting no tests.
