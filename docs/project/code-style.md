# Code Style

## Formatting

gp-libs uses [ruff](https://github.com/astral-sh/ruff) for both linting and formatting.

```console
$ uv run ruff format .
```

```console
$ uv run ruff check . --fix --show-fixes
```

## Type Checking

Strict [mypy](https://mypy-lang.org/) is enforced across `src/` and `tests/`.

```console
$ uv run mypy .
```

## Docstrings

Follow [NumPy docstring style](https://numpydoc.readthedocs.io/en/latest/format.html)
for all public functions, methods, and classes.
