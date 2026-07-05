(linkify_issues-custom-patterns)=

# Custom patterns

`issue_re` optionally changes which plain-text references become links. The
pattern must expose exactly one capturing group. Use a named group when your
`issue_url_tpl` references `{issue_id}`.

The default pattern captures numbered references:

```python
issue_re = r"#(?P<issue_id>\d+)"
```

Capture project-prefixed IDs by keeping one named group:

```python
issue_re = r"#(?P<issue_id>[A-Z]+-\d+)"
issue_url_tpl = "https://github.com/git-pull/gp-libs/issues/{issue_id}"
```

Capture only the numeric part when the prefix should not appear in the URL:

```python
issue_re = r"#ISSUE-(?P<issue_id>\d+)"
issue_url_tpl = "https://github.com/git-pull/gp-libs/issues/{issue_id}"
```

If you need multiple URL fields, use a project-local transform or propose an
extension change; the current transform validates one capturing group.
