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
{mod}`doctest_docutils`, then reports each collected doctest as a pytest item.
That gives documentation examples the same pass/fail surface as the rest of
your suite.

[pytest]: https://docs.pytest.org/en/stable/
