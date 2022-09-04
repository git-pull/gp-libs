(linkify_issues)=
(linkify-issues)=

# Autolink GitHub issues

Automatically link plaintext issues, e.g. `\#1`, as
[#1](https://github.com/git-pull/gp-libs/issues/1).

This is a perfectly legitimately request, even sphinx's own conf.py does a
[non-docutils
hack](https://github.com/sphinx-doc/sphinx/blob/v5.1.1/doc/conf.py#L151-L170) to
link plain-text nodes.

## Configuration

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

### Issue pattern

`issue_re` is available to optionally adjust the pattern plain text is matched
against. By default it is :var:`linkify_issues`

```python
r"#(?P<issue_id>\d+)"
```

Where `^\` negates matches (as seen below) and numbers are matched via `\d`.

You can pass a `str` - which is automatically upcasted when parsing - or a :class:`re.Pattern`. In conf.py, to catch letters and dashes too:

```python
issue_re = r"#(?P<issue_id>[\da-z-]+)"
```

That will match patterns like #ISSUE-34, where `'ISSUE-34'` will be captured.
What you may prefer is just capturing the `34`:

```python
issue_re = r"#ISSUE-(?P<issue_id>\d+)"
```

`issue_url_tpl`'s regex patterns can be extended and passed into `issue_re`'s string formatting:

```python
issue_re = r"#(?P<page_type>(issue|pull)+)-(?P<issue_id>\d+)"
issue_url_tpl = "https://github.com/git-pull/gp-libs/{page_type}/{issue_id}"
```

\#issue-1 will be [#issue-1](https://github.com/git-pull/gp-libs/issue/1)

\#pull-1 will be [#pull-1](https://github.com/git-pull/gp-libs/pull/1)

If your needs are more complex, you may need to fork it for yourself or suggest a PR.

## API

```{eval-rst}
.. automodule:: linkify_issues
   :members:
   :show-inheritance:
   :undoc-members:
```
