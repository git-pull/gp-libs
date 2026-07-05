(linkify_issues-how-to)=

# How-to

In your Sphinx `conf.py`, add the extension:

```python
extensions = [
    "linkify_issues",
]
```

Then configure the issue URL template:

```python
issue_url_tpl = "https://github.com/git-pull/gp-libs/issues/{issue_id}"
```

The default `issue_re` captures the number from text such as `#42`, and
{mod}`linkify_issues` formats `issue_url_tpl` with that captured `issue_id`.
