# gp-libs &middot; [![Python Package](https://img.shields.io/pypi/v/gp-libs.svg)](https://pypi.org/project/gp-libs/) [![License](https://img.shields.io/github/license/git-pull/gp-libs.svg)](https://github.com/git-pull/gp-libs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/git-pull/gp-libs/branch/master/graph/badge.svg)](https://codecov.io/gh/git-pull/gp-libs)

Incubating / [dogfooding] some sphinx extensions and pytest plugins on
git-pull projects, e.g. [cihai], [vcs-python], or [tmux-python].

[dogfooding]: https://en.wikipedia.org/wiki/Eating_your_own_dog_food
[cihai]: https://github.com/cihai
[vcs-python]: https://github.com/vcs-python
[tmux-python]: https://github.com/tmux-python

## doctest helpers (for docutils)

Two parts:

1. doctest module: Same specification as doctest, but can parse reStructuredText
   and markdown
2. pytest plugin: Collects pytest for reStructuredText and markdown files

### doctest module

This extends standard library `doctest` to support anything docutils can parse.
It can parse reStructuredText (.rst) and markdown (.md).

See more: <https://gp-libs.git-pull.com/doctest/>

#### Writing doctests

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

#### Test your docs

##### reStructuredText

```console
$ python -m docutils_doctest README.rst -v
```

That's what `doctest` does by design.

##### Markdown

If you install [myst-parser], doctest will run on .md files.

```console
$ python -m docutils_doctest README.md -v
```

### pytest plugin

This plugin integrates with the above module.

```console
$ pytest docs/
```

Like the above module, it supports docutils' own `doctest_block` and a basic
`.. doctest::` directive.

See more: <https://gp-libs.git-pull.com/doctest/pytest.html>

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

### Table of contents for autodoc

`sphinx.ext.autodoc` doesn't link objects in the table of contents. So we need a
plugin to help.

See more: <https://gp-libs.git-pull.com/sphinx_toctree_signature/>

#### Configuration

1. Add `'sphinx_toctree_signature'` to `extensions`

   ```python
   extensions = [
       # ...
       "sphinx_toctree_signature",
   ]
   ```

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

# More information

- Python support: >= 3.7, pypy
- Source: <https://github.com/git-pull/gp-libs>
- Docs: <https://gp-libs.git-pull.com>
- Changelog: <https://gp-libs.git-pull.com/history.html>
- Issues: <https://github.com/git-pull/gp-libs/issues>
- Test Coverage: <https://codecov.io/gh/git-pull/gp-libs>
- pypi: <https://pypi.python.org/pypi/gp-libs>
- License: [MIT](https://opensource.org/licenses/MIT).

[![Docs](https://github.com/git-pull/gp-libs/workflows/docs/badge.svg)](https://gp-libs.git-pull.com)
[![Build Status](https://github.com/git-pull/gp-libs/workflows/tests/badge.svg)](https://github.com/git-pull/gp-libs/actions?query=workflow%3A%22tests%22)
