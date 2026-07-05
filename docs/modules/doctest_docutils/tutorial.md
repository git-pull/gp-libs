(doctest_docutils-tutorial)=

# Tutorial

Start with a Markdown file that contains one Python prompt example:

````markdown
```python
>>> 2 + 2
4
```
````

Run {mod}`doctest_docutils` against the file:

```console
$ python -m doctest_docutils README.md
```

The command exits successfully when every collected example matches its expected
output. Add `-v` to see which examples ran:

```console
$ python -m doctest_docutils README.md -v
```

The module keeps the standard-library {mod}`doctest` comparison rules and
changes the input layer: documentation is parsed through [docutils], with
[myst-parser] handling Markdown.

[docutils]: https://www.docutils.org/
[myst-parser]: https://myst-parser.readthedocs.io/en/latest/
