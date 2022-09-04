# pytest plugin

The pytest plugin is built on top of the doctest_docutils module, which is in
turn compatible with {mod}`doctest`.

## Markdown

If you install [myst-parser], doctest will run on .md files.

```console
$ pytest README.md
```

[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

## API

```{eval-rst}
.. automodule:: pytest_sphinx
   :members:
   :show-inheritance:
   :undoc-members:
```
