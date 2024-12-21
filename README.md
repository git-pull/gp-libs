# gp-libs &middot; [![Python Package](https://img.shields.io/pypi/v/gp-libs.svg)](https://pypi.org/project/gp-libs/) [![License](https://img.shields.io/github/license/git-pull/gp-libs.svg)](https://github.com/git-pull/gp-libs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/git-pull/gp-libs/branch/master/graph/badge.svg)](https://codecov.io/gh/git-pull/gp-libs)

Incubating / [dogfooding] some sphinx extensions and pytest plugins on
git-pull projects, e.g. [cihai], [vcs-python], or [tmux-python].

[dogfooding]: https://en.wikipedia.org/wiki/Eating_your_own_dog_food
[cihai]: https://github.com/cihai
[vcs-python]: https://github.com/vcs-python
[tmux-python]: https://github.com/tmux-python

## `doctest` for reStructured and markdown

Two components:

1. `doctest_docutils` module: Same specification as `doctest`, but can parse reStructuredText
   and markdown
2. `pytest_doctest_docutils`: Pytest plugin, collects test items for pytest for reStructuredText and markdown files

   This means you can do:

   ```console
   $ pytest docs
   ```

### doctest module

This extends standard library `doctest` to support anything docutils can parse.
It can parse reStructuredText (.rst) and markdown (.md).

See more: <https://gp-libs.git-pull.com/doctest/>

#### Supported styles

It supports two barebones directives:

- docutils' `doctest_block`

  ```rst
  >>> 2 + 2
  4
  ```

- `.. doctest::` directive

  reStructuredText:

  ```rst
  .. doctest::

     >>> 2 + 2
     4
  ```

  Markdown (requires [myst-parser]):

  ````markdown
  ```{doctest}
  >>> 2 + 2
  4
  ```
  ````

[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

#### Usage

The `doctest_docutils` module preserves standard library's usage conventions:

##### reStructuredText

```console
$ python -m doctest_docutils README.rst -v
```

That's what `doctest` does by design.

##### Markdown

If you install [myst-parser], doctest will run on .md files.

```console
$ python -m doctest_docutils README.md -v
```

### pytest plugin

_This plugin disables [pytest's standard `doctest` plugin]._

This plugin integrates with the `doctest_docutils` module with pytest to enable seamless testing of docs, `conftest.py` fixtures and all.

```console
$ pytest docs/
```

Like the above module, it supports docutils' own `doctest_block` and a basic
`.. doctest::` directive.

See more: <https://gp-libs.git-pull.com/doctest/pytest.html>

[pytest's standard `doctest` plugin]: https://docs.pytest.org/en/stable/how-to/doctest.html#doctest

## sphinx plugins

### Plain-text issue linker (`linkify-issues`)

We need to parse plain text, e.g. #99999, to point to the project tracker at
https://github.com/git-pull/gp-libs/issues/99999. This way the markdown looks
good anywhere you render it, including GitHub and GitLab.

#### Configuration

In your _conf.py_:

1. Add `'linkify_issues'` to `extensions`

   ```python
   extensions = [
       # ...
       "linkify_issues",
   ]
   ```

2. Configure your issue URL, `issue_url_tpl`:

   ```python
   # linkify_issues
   issue_url_tpl = 'https://github.com/git-pull/gp-libs/issues/{issue_id}'
   ```

   The config variable is formatted via {meth}`str.format` where `issue_id` is
   `42` if the text is \#42.

See more: <https://gp-libs.git-pull.com/linkify_issues/>

## Install

```console
$ pip install --user gp-libs
```

### Developmental releases

You can test the unpublished version of g before its released.

- [pip](https://pip.pypa.io/en/stable/):

  ```console
  $ pip install --user --upgrade --pre gp-libs
  ```

# Minimum requirements

To lift the development burden of supporting legacy APIs, as this package is
lightly used, minimum constraints have been pinned:

- docutils: 0.20.1+
- myst-parser: 2.0.0+

If you have even passing interested in supporting legacy versions, file an
issue on the tracker.

# More information

- Python support: >= 3.9, pypy
- Source: <https://github.com/git-pull/gp-libs>
- Docs: <https://gp-libs.git-pull.com>
- Changelog: <https://gp-libs.git-pull.com/history.html>
- Issues: <https://github.com/git-pull/gp-libs/issues>
- Test Coverage: <https://codecov.io/gh/git-pull/gp-libs>
- pypi: <https://pypi.python.org/pypi/gp-libs>
- License: [MIT](https://opensource.org/licenses/MIT).

[![Docs](https://github.com/git-pull/gp-libs/workflows/docs/badge.svg)](https://gp-libs.git-pull.com)
[![Build Status](https://github.com/git-pull/gp-libs/workflows/tests/badge.svg)](https://github.com/git-pull/gp-libs/actions?query=workflow%3A%22tests%22)
