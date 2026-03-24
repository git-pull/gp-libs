(index)=

# gp-libs

Test and documentation utilities for [git-pull](https://github.com/git-pull) projects.

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc
Install and get started in minutes.
:::

:::{grid-item-card} doctest_docutils
:link: doctest/index
:link-type: doc
Run doctests in reStructuredText and Markdown files.
:::

:::{grid-item-card} linkify_issues
:link: linkify_issues/index
:link-type: doc
Automatically link `#123` to GitHub issues in Sphinx docs.
:::

:::{grid-item-card} Contributing
:link: project/index
:link-type: doc
Development setup, code style, release process.
:::

::::

## Install

```console
$ pip install gp-libs
```

```console
$ uv add gp-libs
```

## At a glance

Run doctests in Markdown and reStructuredText files:

```console
$ python -m doctest_docutils README.md -v
```

Auto-link issue references in Sphinx documentation:

```python
# conf.py
extensions = ["linkify_issues"]
issue_url_tpl = "https://github.com/myorg/myrepo/issues/{issue_id}"
```

```{toctree}
:hidden:

quickstart
doctest/index
linkify_issues/index
project/index
history
```
