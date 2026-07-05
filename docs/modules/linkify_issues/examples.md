(linkify_issues-examples)=

# Examples

## Default GitHub issues

```python
extensions = ["linkify_issues"]
issue_url_tpl = "https://github.com/git-pull/gp-libs/issues/{issue_id}"
```

With the default pattern, source text such as `#123` links to the matching issue
URL.

## Prefixed issue keys

```python
extensions = ["linkify_issues"]
issue_re = r"#(?P<issue_id>[A-Z]+-\d+)"
issue_url_tpl = "https://github.com/git-pull/gp-libs/issues/{issue_id}"
```

This captures a single value such as `ISSUE-123` and formats it into the URL
template.
