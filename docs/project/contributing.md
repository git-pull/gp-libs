# Contributing

Install [git] and [uv].

Clone:

```console
$ git clone https://github.com/git-pull/gp-libs.git
```

```console
$ cd gp-libs
```

Install packages:

```console
$ uv sync --all-extras --dev
```

## Tests

```console
$ uv run py.test
```

### Automatically run tests on file save

1. `make start` (via [pytest-watcher])
2. `make watch_test` (requires installing [entr(1)])

[pytest-watcher]: https://github.com/olzhasar/pytest-watcher

## Documentation

Default preview server: http://localhost:8034

[sphinx-autobuild] will automatically build the docs, watch for file changes and launch a server.

From home directory: `make start_docs`
From inside `docs/`: `make start`

[sphinx-autobuild]: https://github.com/executablebooks/sphinx-autobuild

### Manual documentation (the hard way)

`cd docs/` and `make html` to build. `make serve` to start http server.

Helpers:
`make build_docs`, `make serve_docs`

Rebuild docs on file change: `make watch_docs` (requires [entr(1)])

Rebuild docs and run server via one terminal: `make dev_docs` (requires above, and a
`make(1)` with `-J` support, e.g. GNU Make)

[git]: https://git-scm.com/
[uv]: https://github.com/astral-sh/uv
[entr(1)]: http://eradman.com/entrproject/
[`entr(1)`]: http://eradman.com/entrproject/
