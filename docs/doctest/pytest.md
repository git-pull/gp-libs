(pytest_plugin)=
(pytest_doctest_docutils)=

# pytest plugin

{mod}`pytest_doctest_docutils` lets pytest collect doctests from `.rst` and
`.md` files. Point [pytest] at a documentation file or directory, and the
plugin parses the page through {ref}`doctest_docutils` before pytest runs the
examples.

The plugin disables {ref}`pytest's standard doctest plugin <pytest:doctest>` by
default so the same examples are not collected twice.

## File support

### reStructuredText (`.rst`)

Run a single reStructuredText file:

```console
$ pytest README.rst
```

Run a documentation directory:

```console
$ pytest docs/
```

### Markdown (`.md`)

Install [myst-parser] when you want pytest to collect doctests from Markdown:

```console
$ pytest README.md
```

Run Markdown and reStructuredText files together from `docs/`:

```console
$ pytest docs/
```

[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

## Using fixtures

Normal pytest fixture visibility applies: {ref}`a visible conftest.py must be
available <pytest:about-fixtures>` for the documentation file being tested. If
`README.md` lives in the project root, put the fixture in a root-level
`conftest.py`:

```python
import pytest


@pytest.fixture
def username():
    return "username"
```

Then a root-level `README.rst` can use the fixture in its doctest examples.

Run the file directly:

```console
$ pytest README.rst
```

For doctests under `docs/`, put the fixtures in `docs/conftest.py` or another
`conftest.py` that pytest can see from that directory:

```text
docs/
    conftest.py
    usage.rst
```

Run the directory:

```console
$ pytest docs/
```

## Python module doctests

Use `--doctest-docutils-modules` when you also want this plugin to collect
Python-module doctests:

```console
$ py.test src/ --doctest-docutils-modules
```

Disable Python-module collection explicitly with `--no-doctest-docutils-modules`:

```console
$ py.test src/ --no-doctest-docutils-modules
```

## Case examples

- [libtmux] ([source](https://github.com/tmux-python/libtmux/tree/v0.15.0post0)):

  - Documentation doctests:

    - [README.md](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/README.md) ([raw](https://github.com/tmux-python/libtmux/raw/v0.15.0post0/README.md))

      _Note: `pytest README.md` requires you have a `conftest.py` directly in the project root_

    - [docs/topics/traversal.md](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/docs/topics/traversal.md) ([raw](https://github.com/tmux-python/libtmux/raw/v0.15.0post0/docs/topics/traversal.md))

  - Configuration:

    - Doctests support pytest fixtures through {ref}`doctest_namespace <pytest:doctest_namespace>`

      See [`add_doctest_fixtures()`](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/src/libtmux/conftest.py#L15-L26) in [`src/libtmux/conftest.py`](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/src/libtmux/conftest.py)

[libtmux]: https://libtmux.git-pull.com/
[pytest]: https://docs.pytest.org/en/stable/

## API

```{eval-rst}
.. automodule:: pytest_doctest_docutils
   :members:
   :show-inheritance:
   :undoc-members:
```
