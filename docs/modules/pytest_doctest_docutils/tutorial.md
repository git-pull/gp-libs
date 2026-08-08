(pytest_doctest_docutils-tutorial)=

# Tutorial

Install gp-libs, put doctest examples in a Markdown or reStructuredText file,
and point [pytest] at the file:

```console
$ pytest README.md
```

Run a documentation directory the same way:

```console
$ pytest docs/
```

{mod}`pytest_doctest_docutils` parses each matching documentation file with
{mod}`doctest_docutils`, then reports each projected shared-state group as one
pytest item. Bare prompt blocks without a group stamp are isolated by default;
unargumented `doctest` directives join Sphinx's `default` group. Named blocks in
the same group share fixtures and Python globals, and execute together as one
schedulable item.

[pytest]: https://docs.pytest.org/en/stable/
