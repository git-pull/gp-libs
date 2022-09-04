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

### pytest plugin

...

This plugin integrates with the above module.

```console
$ pytest docs/
```

Like the above module, it supports docutils' own `doctest_block` and a basic
`.. doctest::` directive.

## sphinx plugins

### Plain-text issue linker (`linkify-issues`)

We need to parse plain text, e.g. #99999, to point to the project tracker at
https://github.com/git-pull/gp-libs/issues/99999. This way the markdown looks
good anywhere you render it, including GitHub and GitLab.

### Table of contents for autodoc

`sphinx.ext.autodoc` doesn't link objects in the table of contents. So we need a
plugin to help.

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
- API: <https://gp-libs.git-pull.com/api.html>
- Issues: <https://github.com/git-pull/gp-libs/issues>
- Test Coverage: <https://codecov.io/gh/git-pull/gp-libs>
- pypi: <https://pypi.python.org/pypi/gp-libs>
- License: [MIT](https://opensource.org/licenses/MIT).

[![Docs](https://github.com/git-pull/gp-libs/workflows/docs/badge.svg)](https://gp-libs.git-pull.com)
[![Build Status](https://github.com/git-pull/gp-libs/workflows/tests/badge.svg)](https://github.com/git-pull/gp-libs/actions?query=workflow%3A%22tests%22)
