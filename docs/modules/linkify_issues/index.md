(linkify_issues)=
(linkify-issues)=

# linkify_issues

{mod}`linkify_issues` is a [Sphinx] extension that turns plain issue references
such as `#1` into links such as [#1](https://github.com/git-pull/gp-libs/issues/1).
Add the extension and set `issue_url_tpl`; the default pattern already handles
numbered GitHub issues.

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} How-to
:link: how-to
:link-type: doc
Configure the default GitHub issue-link workflow.
:::

:::{grid-item-card} Custom Patterns
:link: custom-patterns
:link-type: doc
Tune the one-group issue pattern safely.
:::

:::{grid-item-card} Examples
:link: examples
:link-type: doc
See default and custom issue-link snippets.
:::

:::{grid-item-card} API Reference
:link: reference
:link-type: doc
Inspect the Sphinx transform and setup hook.
:::

::::

```{toctree}
:hidden:

how-to
custom-patterns
examples
reference
```

[Sphinx]: https://www.sphinx-doc.org/
