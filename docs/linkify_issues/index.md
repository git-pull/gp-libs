(linkify_issues)=
(linkify-issues)=

# Autolink GitHub issues

The {mod}`linkify_issues` [Sphinx] extension turns plain issue references such
as `\#1` into links such as [#1](https://github.com/git-pull/gp-libs/issues/1).
Add the extension and set `issue_url_tpl`; the default pattern already handles
numbered GitHub issues.

This keeps issue references readable in source while making rendered Sphinx
pages easier to navigate. Sphinx's own `conf.py` uses a
[non-docutils hook](https://github.com/sphinx-doc/sphinx/blob/v5.1.1/doc/conf.py#L151-L170)
for the same plain-text linking problem.

## Configuration

In your `conf.py`:

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

### Issue pattern

`issue_re` optionally adjusts the plain-text pattern. By default it matches
numbered references:

```python
r"#(?P<issue_id>\d+)"
```

The named `issue_id` group is passed into `issue_url_tpl`. Numbers are matched
with `\d`.

You can pass a {class}`str`, which is compiled while parsing, or a
{class}`re.Pattern`. In `conf.py`, catch letters and dashes too:

```python
issue_re = r"#(?P<issue_id>[\da-z-]+)"
```

That matches patterns like `#ISSUE-34`, where `'ISSUE-34'` is captured.
What you may prefer is just capturing the `34`:

```python
issue_re = r"#ISSUE-(?P<issue_id>\d+)"
```

Named groups from `issue_re` are also available to `issue_url_tpl`:

```python
issue_re = r"#(?P<page_type>(issue|pull)+)-(?P<issue_id>\d+)"
issue_url_tpl = "https://github.com/git-pull/gp-libs/{page_type}/{issue_id}"
```

`\#issue-1` becomes [#issue-1](https://github.com/git-pull/gp-libs/issue/1).

`\#pull-1` becomes [#pull-1](https://github.com/git-pull/gp-libs/pull/1).

If your needs are more complex, you may need to fork it for yourself or suggest a PR.

## API

```{eval-rst}
.. automodule:: linkify_issues
   :members:
   :show-inheritance:
   :undoc-members:
```

[Sphinx]: https://www.sphinx-doc.org/
